from types import SimpleNamespace

from app.voice import stt as stt_module


class FakeTranscriptions:
    def __init__(self, response):
        self.response = response
        self.arguments = None

    def create(self, **kwargs):
        self.arguments = kwargs
        return self.response


class FakeClient:
    def __init__(self, response):
        self.audio = SimpleNamespace(
            transcriptions=FakeTranscriptions(response)
        )


def make_stt(monkeypatch, response):
    client = FakeClient(response)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(
        stt_module,
        "Groq",
        lambda api_key: client,
    )
    return stt_module.GroqSTT(), client


def test_transcription_without_metadata_returns_language_none(
    monkeypatch,
    tmp_path,
):
    stt, client = make_stt(
        monkeypatch,
        SimpleNamespace(text="hello"),
    )
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"audio")

    result = stt.transcribe(audio_path)

    assert result["success"] is True
    assert result["text"] == "hello"
    assert result["language"] is None
    assert result["language_source"] == "unknown"
    assert client.audio.transcriptions.arguments["response_format"] == (
        "verbose_json"
    )


def test_transcription_uses_dynamic_language_attribute(
    monkeypatch,
    tmp_path,
):
    stt, _ = make_stt(
        monkeypatch,
        SimpleNamespace(text="hello", language="en"),
    )
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"audio")

    result = stt.transcribe(audio_path)

    assert result["language"] == "en"
    assert result["language_source"] == "detected"


def test_transcription_uses_model_extra_language(
    monkeypatch,
    tmp_path,
):
    stt, _ = make_stt(
        monkeypatch,
        SimpleNamespace(
            text="namaste",
            model_extra={"language": "te"},
        ),
    )
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"audio")

    result = stt.transcribe(audio_path)

    assert result["language"] == "te"
    assert result["language_source"] == "detected"


def test_explicit_language_is_fallback_when_metadata_is_absent(
    monkeypatch,
    tmp_path,
):
    stt, _ = make_stt(
        monkeypatch,
        SimpleNamespace(text="hello"),
    )
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"audio")

    result = stt.transcribe(audio_path, language="en")

    assert result["language"] == "en"
    assert result["language_source"] == "requested_fallback"


def test_malformed_language_metadata_does_not_crash(
    monkeypatch,
    tmp_path,
):
    stt, _ = make_stt(
        monkeypatch,
        SimpleNamespace(
            text="hello",
            language=object(),
            model_extra="invalid",
        ),
    )
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"audio")

    result = stt.transcribe(audio_path)

    assert result["success"] is True
    assert result["language"] is None
    assert result["language_source"] == "unknown"