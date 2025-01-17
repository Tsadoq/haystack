import os
from unittest.mock import patch
from pathlib import Path

import openai
import pytest
from openai.util import convert_to_openai_object

from haystack.components.audio.whisper_remote import RemoteWhisperTranscriber
from haystack.dataclasses import ByteStream


def mock_openai_response(response_format="json", **kwargs) -> openai.openai_object.OpenAIObject:
    if response_format == "json":
        dict_response = {"text": "test transcription"}
    # Currently only "json" is supported.
    else:
        dict_response = {}

    return convert_to_openai_object(dict_response)


class TestRemoteWhisperTranscriber:
    def test_init_no_key(self, monkeypatch):
        openai.api_key = None
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        error_msg = "RemoteWhisperTranscriber expects an OpenAI API key."
        with pytest.raises(ValueError, match=error_msg):
            RemoteWhisperTranscriber(api_key=None)

    def test_init_key_env_var(self, monkeypatch):
        openai.api_key = None
        monkeypatch.setenv("OPENAI_API_KEY", "test_api_key")
        RemoteWhisperTranscriber(api_key=None)
        assert openai.api_key == "test_api_key"

    def test_init_key_module_env_and_global_var(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test_api_key_2")
        openai.api_key = "test_api_key_1"
        RemoteWhisperTranscriber(api_key=None)
        # The module global variable takes preference
        assert openai.api_key == "test_api_key_1"

    def test_init_default(self):
        transcriber = RemoteWhisperTranscriber(api_key="test_api_key")

        assert openai.api_key == "test_api_key"
        assert transcriber.model_name == "whisper-1"
        assert transcriber.organization is None
        assert transcriber.api_base_url == "https://api.openai.com/v1"
        assert transcriber.whisper_params == {"response_format": "json"}

    def test_init_custom_parameters(self):
        transcriber = RemoteWhisperTranscriber(
            api_key="test_api_key",
            model_name="whisper-1",
            organization="test-org",
            api_base_url="test_api_url",
            language="en",
            prompt="test-prompt",
            response_format="json",
            temperature="0.5",
        )

        assert openai.api_key == "test_api_key"
        assert transcriber.model_name == "whisper-1"
        assert transcriber.organization == "test-org"
        assert transcriber.api_base_url == "test_api_url"
        assert transcriber.whisper_params == {
            "language": "en",
            "prompt": "test-prompt",
            "response_format": "json",
            "temperature": "0.5",
        }

    def test_to_dict_default_parameters(self):
        transcriber = RemoteWhisperTranscriber(api_key="test_api_key")
        data = transcriber.to_dict()
        assert data == {
            "type": "haystack.components.audio.whisper_remote.RemoteWhisperTranscriber",
            "init_parameters": {
                "model_name": "whisper-1",
                "api_base_url": "https://api.openai.com/v1",
                "organization": None,
                "response_format": "json",
            },
        }

    def test_to_dict_with_custom_init_parameters(self):
        transcriber = RemoteWhisperTranscriber(
            api_key="test_api_key",
            model_name="whisper-1",
            organization="test-org",
            api_base_url="test_api_url",
            language="en",
            prompt="test-prompt",
            response_format="json",
            temperature="0.5",
        )
        data = transcriber.to_dict()
        assert data == {
            "type": "haystack.components.audio.whisper_remote.RemoteWhisperTranscriber",
            "init_parameters": {
                "model_name": "whisper-1",
                "organization": "test-org",
                "api_base_url": "test_api_url",
                "language": "en",
                "prompt": "test-prompt",
                "response_format": "json",
                "temperature": "0.5",
            },
        }

    def test_from_dict_with_defualt_parameters(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test_api_key")

        data = {
            "type": "haystack.components.audio.whisper_remote.RemoteWhisperTranscriber",
            "init_parameters": {
                "model_name": "whisper-1",
                "api_base_url": "https://api.openai.com/v1",
                "organization": None,
                "response_format": "json",
            },
        }

        transcriber = RemoteWhisperTranscriber.from_dict(data)

        assert openai.api_key == "test_api_key"
        assert transcriber.model_name == "whisper-1"
        assert transcriber.organization is None
        assert transcriber.api_base_url == "https://api.openai.com/v1"
        assert transcriber.whisper_params == {"response_format": "json"}

    def test_from_dict_with_custom_init_parameters(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test_api_key")

        data = {
            "type": "haystack.components.audio.whisper_remote.RemoteWhisperTranscriber",
            "init_parameters": {
                "model_name": "whisper-1",
                "organization": "test-org",
                "api_base_url": "test_api_url",
                "language": "en",
                "prompt": "test-prompt",
                "response_format": "json",
                "temperature": "0.5",
            },
        }
        transcriber = RemoteWhisperTranscriber.from_dict(data)

        assert openai.api_key == "test_api_key"
        assert transcriber.model_name == "whisper-1"
        assert transcriber.organization == "test-org"
        assert transcriber.api_base_url == "test_api_url"
        assert transcriber.whisper_params == {
            "language": "en",
            "prompt": "test-prompt",
            "response_format": "json",
            "temperature": "0.5",
        }

    def test_from_dict_with_defualt_parameters_no_env_var(self, monkeypatch):
        openai.api_key = None
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        data = {
            "type": "haystack.components.audio.whisper_remote.RemoteWhisperTranscriber",
            "init_parameters": {
                "model_name": "whisper-1",
                "api_base_url": "https://api.openai.com/v1",
                "organization": None,
                "response_format": "json",
            },
        }

        with pytest.raises(ValueError, match="RemoteWhisperTranscriber expects an OpenAI API key."):
            RemoteWhisperTranscriber.from_dict(data)

    def test_run_str(self, test_files_path):
        with patch("haystack.components.audio.whisper_remote.openai.Audio") as openai_audio_patch:
            model = "whisper-1"
            file_path = str(test_files_path / "audio" / "this is the content of the document.wav")
            openai_audio_patch.transcribe.side_effect = mock_openai_response

            transcriber = RemoteWhisperTranscriber(api_key="test_api_key", model_name=model, response_format="json")
            result = transcriber.run(sources=[file_path])

            assert result["documents"][0].content == "test transcription"
            assert result["documents"][0].meta["file_path"] == file_path

    def test_run_path(self, test_files_path):
        with patch("haystack.components.audio.whisper_remote.openai.Audio") as openai_audio_patch:
            model = "whisper-1"
            file_path = test_files_path / "audio" / "this is the content of the document.wav"
            openai_audio_patch.transcribe.side_effect = mock_openai_response

            transcriber = RemoteWhisperTranscriber(api_key="test_api_key", model_name=model, response_format="json")
            result = transcriber.run(sources=[file_path])

            assert result["documents"][0].content == "test transcription"
            assert result["documents"][0].meta["file_path"] == file_path

    def test_run_bytestream(self, test_files_path):
        with patch("haystack.components.audio.whisper_remote.openai.Audio") as openai_audio_patch:
            model = "whisper-1"
            file_path = test_files_path / "audio" / "this is the content of the document.wav"
            openai_audio_patch.transcribe.side_effect = mock_openai_response

            transcriber = RemoteWhisperTranscriber(api_key="test_api_key", model_name=model, response_format="json")
            with open(file_path, "rb") as audio_stream:
                byte_stream = audio_stream.read()
                audio_file = ByteStream(byte_stream, metadata={"file_path": str(file_path.absolute())})

                result = transcriber.run(sources=[audio_file])

                assert result["documents"][0].content == "test transcription"
                assert result["documents"][0].meta["file_path"] == str(file_path.absolute())

    @pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY", None),
        reason="Export an env var called OPENAI_API_KEY containing the OpenAI API key to run this test.",
    )
    @pytest.mark.integration
    def test_whisper_remote_transcriber(self, test_files_path):
        transcriber = RemoteWhisperTranscriber(api_key=os.environ.get("OPENAI_API_KEY"))

        paths = [
            test_files_path / "audio" / "this is the content of the document.wav",
            str(test_files_path / "audio" / "the context for this answer is here.wav"),
            ByteStream.from_file_path(test_files_path / "audio" / "answer.wav"),
        ]

        output = transcriber.run(sources=paths)

        docs = output["documents"]
        assert len(docs) == 3
        assert docs[0].content.strip().lower() == "this is the content of the document."
        assert test_files_path / "audio" / "this is the content of the document.wav" == docs[0].meta["file_path"]

        assert docs[1].content.strip().lower() == "the context for this answer is here."
        assert str(test_files_path / "audio" / "the context for this answer is here.wav") == docs[1].meta["file_path"]

        assert docs[2].content.strip().lower() == "answer."
