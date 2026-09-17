import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


class GroqSTT:
    """Speech-to-text service using Groq's Whisper model."""

    @staticmethod
    def _extract_detected_language(transcription: Any) -> str | None:
        """Read optional language metadata from a Groq response safely."""

        try:
            language = getattr(transcription, "language", None)
        except Exception:
            language = None

        if isinstance(language, str) and language.strip():
            return language.strip()

        try:
            metadata = getattr(transcription, "model_extra", None)
        except Exception:
            metadata = None

        if isinstance(metadata, dict):
            language = metadata.get("language")

            if isinstance(language, str) and language.strip():
                return language.strip()

        return None

    def __init__(
        self,
        model: str = "whisper-large-v3-turbo",
    ) -> None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY was not found in the environment."
            )

        self.client = Groq(api_key=api_key)
        self.model = model

    def transcribe(
        self,
        audio_path: str | Path,
        language: str | None = None,
    ) -> dict[str, Any]:
        """
        Transcribe an audio file using Groq Whisper.

        Args:
            audio_path: Path to the WAV/audio file.
            language: Optional language code such as 'en' or 'te'.

        Returns:
            Structured transcription result.
        """

        audio_path = Path(audio_path)

        if not audio_path.exists():
            return {
                "success": False,
                "text": "",
                "message": f"Audio file not found: {audio_path}",
            }

        if not audio_path.is_file():
            return {
                "success": False,
                "text": "",
                "message": f"Audio path is not a file: {audio_path}",
            }

        try:
            with audio_path.open("rb") as audio_file:
                request_kwargs: dict[str, Any] = {
                    "file": audio_file,
                    "model": self.model,
                    "response_format": "verbose_json",
                }

                if language:
                    request_kwargs["language"] = language

                transcription = self.client.audio.transcriptions.create(
                    **request_kwargs
                )

            text = transcription.text.strip()
            detected_language = self._extract_detected_language(
                transcription
            )
            language_source = "detected"

            if detected_language is None:
                if language:
                    detected_language = language
                    language_source = "requested_fallback"
                else:
                    language_source = "unknown"

            return {
                "success": True,
                "text": text,
                "language": detected_language,
                "language_source": language_source,
                "model": self.model,
                "message": "Audio transcribed successfully.",
            }

        except Exception as exc:
            return {
                "success": False,
                "text": "",
                "message": f"Speech transcription failed: {exc}",
            }


if __name__ == "__main__":
    stt = GroqSTT()

    result = stt.transcribe(
        audio_path="recording.wav",
    )

    print(result)