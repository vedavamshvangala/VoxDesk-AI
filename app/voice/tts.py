from pathlib import Path
from typing import Any

import pyttsx3


class WindowsTTS:
    """Offline Windows text-to-speech through SAPI5 and pyttsx3."""

    DEFAULT_RATE = 150
    DEFAULT_VOLUME = 1.0

    LANGUAGE_ALIASES = {
        "en": "en",
        "english": "en",
        "te": "te",
        "telugu": "te",
        "te-en": "te-en",
        "en-te": "te-en",
        "telugu-english": "te-en",
        "english-telugu": "te-en",
    }

    def __init__(
        self,
        voice_name: str | None = "Microsoft David",
        rate: int = DEFAULT_RATE,
        volume: float = DEFAULT_VOLUME,
    ) -> None:
        self.engine = pyttsx3.init("sapi5")
        self.rate = rate
        self.volume = volume
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)
        self.voice_name = voice_name
        self.voice_id: str | None = None
        self._voices = self._discover_voices()

        if voice_name is not None:
            requested_voice = self._find_voice_by_name(voice_name)

            if requested_voice is None:
                available = [voice["name"] for voice in self._voices]
                raise ValueError(
                    f"Voice '{voice_name}' was not found. "
                    f"Available voices: {available}"
                )

            self.voice_id = requested_voice["id"]
            self.engine.setProperty("voice", self.voice_id)
        elif self._voices:
            self.voice_id = self._voices[0]["id"]
            self.engine.setProperty("voice", self.voice_id)

    @classmethod
    def _normalize_language(cls, language: str) -> str | None:
        if not isinstance(language, str):
            return None

        return cls.LANGUAGE_ALIASES.get(language.strip().lower())

    @staticmethod
    def _language_values(voice: Any) -> list[str]:
        languages = getattr(voice, "languages", [])

        if isinstance(languages, (str, bytes)):
            languages = [languages]

        if not isinstance(languages, (list, tuple)):
            return []

        values = []

        for value in languages:
            if isinstance(value, bytes):
                value = value.decode("utf-8", errors="ignore")

            if value is not None:
                values.append(str(value).lower())

        return values

    @classmethod
    def _voice_languages(cls, voice: Any) -> set[str]:
        languages = cls._language_values(voice)
        name = str(getattr(voice, "name", "")).lower()
        identifier = str(getattr(voice, "id", "")).lower()
        combined = " ".join(languages + [name, identifier])
        supported = set()

        if any(
            marker in combined
            for marker in (
                "409",
                "en-us",
                "en_us",
                "en-gb",
                "en_gb",
                "english",
            )
        ):
            supported.add("en")

        if any(
            marker in combined
            for marker in ("te-in", "te_in", "telugu", "0x44a", "044a")
        ):
            supported.add("te")

        return supported

    def _discover_voices(self) -> list[dict[str, Any]]:
        try:
            voices = self.engine.getProperty("voices") or []
        except Exception:
            return []

        results = []

        for index, voice in enumerate(voices):
            voice_id = getattr(voice, "id", None)

            if not isinstance(voice_id, str) or not voice_id:
                continue

            results.append(
                {
                    "index": index,
                    "id": voice_id,
                    "name": str(getattr(voice, "name", "") or ""),
                    "languages": self._language_values(voice),
                    "supported_languages": sorted(
                        self._voice_languages(voice)
                    ),
                    "gender": getattr(voice, "gender", None),
                    "age": getattr(voice, "age", None),
                }
            )

        return results

    def _find_voice_by_name(self, voice_name: str) -> dict[str, Any] | None:
        requested = voice_name.strip().lower()

        for voice in self._voices:
            if requested in voice["name"].lower():
                return voice

        return None

    def list_voices(self) -> list[dict[str, Any]]:
        """Return discovered SAPI5 voices and their language capabilities."""

        return [dict(voice) for voice in self._voices]

    def find_voice_for_language(self, language: str) -> dict[str, Any] | None:
        """Find a voice supporting the requested normalized language."""

        normalized = self._normalize_language(language)

        if normalized is None:
            return None

        required = {"en", "te"} if normalized == "te-en" else {normalized}

        for voice in self._voices:
            if required.issubset(set(voice["supported_languages"])):
                return dict(voice)

        return None

    def is_language_supported(self, language: str) -> bool:
        return self.find_voice_for_language(language) is not None

    def select_voice_for_language(self, language: str) -> dict[str, Any]:
        """Select a compatible voice without falling back across languages."""

        normalized = self._normalize_language(language)
        voice = self.find_voice_for_language(language)

        if normalized is None:
            return {
                "success": False,
                "language": language,
                "voice_available": False,
                "fallback": False,
                "message": f"Unsupported TTS language: {language}",
            }

        if voice is None:
            return {
                "success": False,
                "language": normalized,
                "voice_available": False,
                "fallback": False,
                "message": (
                    f"No installed SAPI5 voice supports language "
                    f"'{normalized}'."
                ),
            }

        self.voice_id = voice["id"]
        self.voice_name = voice["name"]
        self.engine.setProperty("voice", self.voice_id)

        return {
            "success": True,
            "language": normalized,
            "voice_available": True,
            "fallback": False,
            "voice": self.voice_id,
            "voice_name": self.voice_name,
            "message": "TTS voice selected successfully.",
        }

    def get_status(self) -> dict[str, Any]:
        return {
            "success": True,
            "backend": "pyttsx3/sapi5",
            "voice": self.voice_id,
            "voice_name": self.voice_name,
            "rate": self.rate,
            "volume": self.volume,
            "voices": len(self._voices),
            "supported_languages": {
                "en": self.is_language_supported("en"),
                "te": self.is_language_supported("te"),
                "te-en": self.is_language_supported("te-en"),
            },
        }

    def speak(self, text: str, language: str = "en") -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            return {
                "success": False,
                "language": self._normalize_language(language) or language,
                "voice_available": False,
                "fallback": False,
                "message": "TTS input text is empty.",
                "text": text,
            }

        selection = self.select_voice_for_language(language)

        if not selection["success"]:
            return {
                **selection,
                "text": text,
            }

        try:
            self.engine.say(text.strip())
            self.engine.runAndWait()

            return {
                **selection,
                "text": text.strip(),
                "rate": self.rate,
                "volume": self.volume,
                "message": "Speech played successfully.",
            }
        except Exception as exc:
            return {
                "success": False,
                "language": selection["language"],
                "voice_available": True,
                "fallback": False,
                "text": text,
                "message": f"Speech playback failed: {exc}",
            }

    def speak_response(self, text: str, language: str = "en") -> dict[str, Any]:
        return self.speak(text, language=language)

    def save(
        self,
        text: str,
        filename: str | Path,
        language: str = "en",
    ) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            return {
                "success": False,
                "language": self._normalize_language(language) or language,
                "voice_available": False,
                "fallback": False,
                "message": "TTS input text is empty.",
                "path": None,
            }

        selection = self.select_voice_for_language(language)

        if not selection["success"]:
            return {
                **selection,
                "path": None,
            }

        output_path = Path(filename)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.engine.save_to_file(text.strip(), str(output_path))
            self.engine.runAndWait()

            return {
                **selection,
                "text": text.strip(),
                "path": str(output_path),
                "message": "Speech saved successfully.",
            }
        except Exception as exc:
            return {
                "success": False,
                "language": selection["language"],
                "voice_available": True,
                "fallback": False,
                "path": str(output_path),
                "message": f"Speech file generation failed: {exc}",
            }

    def save_to_file(
        self,
        text: str,
        output_path: str | Path,
    ) -> dict[str, Any]:
        """Backward-compatible English save wrapper."""

        return self.save(text, output_path, language="en")

    def stop(self) -> None:
        try:
            self.engine.stop()
        except Exception:
            pass
