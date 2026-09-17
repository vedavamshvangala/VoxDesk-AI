import re
from typing import Any


class VoiceLanguageClassifier:
    """Classify voice text using deterministic language signals only."""

    ROMANIZED_TELUGU_MARKERS = {
        "cheyyi",
        "cheyyandi",
        "chesi",
        "lo",
        "ani",
        "ki",
        "ku",
        "undi",
        "ivvu",
        "pettu",
        "teesi",
        "choopu",
    }

    ENGLISH_CONTROL_WORDS = {
        "and",
        "close",
        "find",
        "go",
        "launch",
        "navigate",
        "open",
        "play",
        "run",
        "search",
        "start",
        "the",
        "then",
        "type",
    }

    ENGLISH_ENTITIES = {
        "calculator",
        "hyderabad",
        "india",
        "notepad",
        "paint",
        "telugu",
        "youtube",
    }

    APPLICATION_NAMES = {
        "calculator",
        "notepad",
        "paint",
    }

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())

    @staticmethod
    def _telugu_script_count(text: str) -> int:
        return sum(
            1
            for character in text
            if "\u0c00" <= character <= "\u0c7f"
        )

    @staticmethod
    def _normalize_metadata(language: str | None) -> str | None:
        if not isinstance(language, str):
            return None

        value = language.strip().lower().replace("_", "-")

        if value in {"te", "tel", "telugu"}:
            return "te"

        if value in {"en", "eng", "english"}:
            return "en"

        return value or None

    def classify(
        self,
        raw_text: str,
        normalized_text: str | None = None,
        stt_language: str | None = None,
        language_source: str | None = None,
    ) -> dict[str, Any]:
        """Return language metadata without changing either text value."""

        raw_value = raw_text if isinstance(raw_text, str) else ""
        metadata_language = self._normalize_metadata(stt_language)
        tokens = self._tokens(raw_value)
        marker_tokens = [
            token
            for token in tokens
            if token in self.ROMANIZED_TELUGU_MARKERS
        ]
        script_count = self._telugu_script_count(raw_value)
        english_payload = [
            token
            for token in tokens
            if token not in self.ROMANIZED_TELUGU_MARKERS
            and token not in self.ENGLISH_CONTROL_WORDS
            and token not in self.APPLICATION_NAMES
        ]
        english_entity_count = sum(
            token in self.ENGLISH_ENTITIES
            for token in english_payload
        )
        strong_romanized = len(marker_tokens) >= 1 and (
            len(marker_tokens) >= 2
            or any(token in {"cheyyi", "cheyyandi", "chesi"} for token in marker_tokens)
        )
        code_switched = strong_romanized and bool(english_payload)
        signals: list[str] = []

        if metadata_language == "te" and language_source != "requested_fallback":
            signals.append("stt_detected_te")
        elif metadata_language == "en" and language_source != "requested_fallback":
            signals.append("stt_detected_en")

        if script_count:
            signals.append("telugu_script_supporting")
        if marker_tokens:
            signals.append("romanized_telugu_markers:" + ",".join(marker_tokens))
        if english_entity_count:
            signals.append("english_entities")

        if script_count and not english_payload:
            language = "te"
            confidence = 0.94
        elif metadata_language == "te" and language_source != "requested_fallback":
            language = "te-en" if code_switched else "te"
            confidence = 0.94 if not code_switched else 0.88
        elif strong_romanized:
            language = "te-en" if code_switched else "te"
            confidence = 0.78 if metadata_language == "en" else 0.88
        else:
            language = "en"
            confidence = 0.88 if metadata_language == "en" else 0.62

        ambiguous = False

        if metadata_language == "en" and strong_romanized:
            ambiguous = True
            confidence = min(confidence, 0.68)
            signals.append("stt_text_conflict")

        if metadata_language not in {None, "en", "te"}:
            ambiguous = True
            confidence = min(confidence, 0.5)
            signals.append("unsupported_stt_language")

        if not raw_value.strip():
            language = "en"
            confidence = 0.0
            ambiguous = True
            signals.append("empty_text")

        source = "combined" if metadata_language and signals else "text_signals"
        if metadata_language and not strong_romanized and not script_count:
            source = "stt_metadata"

        return {
            "language": language,
            "confidence": float(confidence),
            "ambiguous": ambiguous,
            "source": source,
            "stt_language": metadata_language,
            "language_source": language_source,
            "raw_text": raw_value,
            "normalized_text": normalized_text,
            "signals": signals,
        }