import re
from difflib import SequenceMatcher


class VoiceCommandNormalizer:
    """
    Conservative normalization layer for speech-to-text output.

    The normalizer is intentionally limited:
    - Corrects high-confidence application-name variations.
    - Handles common speech/phonetic distortions.
    - Removes accidental repeated transcription.
    - Preserves user-provided command content.
    - Does not rewrite entire sentences.
    """

    APPLICATION_ALIASES = {
        "notepad": [
            "notepad",
            "note pad",
            "node pad",
            "node bar",
            "note bad",
            "node bad",
        ],
        "calculator": [
            "calculator",
            "calculate",
            "calculated",
            "cal culator",
        ],
        "file explorer": [
            "file explorer",
            "file emplorer",
            "windows explorer",
            "windows file explorer",
        ],
        "paint": [
            "paint",
            "ms paint",
            "microsoft paint",
        ],
        "command prompt": [
            "command prompt",
            "cmd",
            "command prom",
        ],
        "vscode": [
            "vs code",
            "visual studio code",
            "visual studio",
            "vs-code",
        ],
        "youtube": [
            "youtube",
            "you tube",
            "you-tube",
        ],
    }

    COMMAND_WORDS = {
        "open",
        "start",
        "launch",
        "run",
    }

    def normalize(self, text: str) -> dict:
        """
        Normalize a Whisper transcription conservatively.

        Returns both original and normalized text so that STT
        quality can still be evaluated independently.
        """

        if not isinstance(text, str):
            return {
                "success": False,
                "original_text": "",
                "normalized_text": "",
                "changed": False,
                "corrections": [],
                "message": "Input transcription must be a string.",
            }

        original_text = text.strip()

        if not original_text:
            return {
                "success": False,
                "original_text": "",
                "normalized_text": "",
                "changed": False,
                "corrections": [],
                "message": "Transcription is empty.",
            }

        normalized = self._clean_text(original_text)

        corrections = []

        # Step 1: remove exact repeated Whisper output.
        deduplicated = self._remove_repeated_phrase(normalized)

        if deduplicated != normalized:
            corrections.append("removed_repeated_transcription")
            normalized = deduplicated

        # Step 2: correct explicit application aliases.
        normalized, app_corrections = self._normalize_applications(
            normalized
        )

        corrections.extend(app_corrections)

        # Step 3: conservative fuzzy application correction.
        normalized, fuzzy_correction = (
            self._high_confidence_fuzzy_app_correction(
                normalized
            )
        )

        if fuzzy_correction:
            corrections.append(fuzzy_correction)

        normalized = self._clean_text(normalized)

        return {
            "success": True,
            "original_text": original_text,
            "normalized_text": normalized,
            "changed": normalized.lower() != original_text.lower(),
            "corrections": corrections,
            "message": "Voice command normalized successfully.",
        }

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalize whitespace."""

        return re.sub(r"\s+", " ", text.strip())

    @staticmethod
    def _remove_repeated_phrase(text: str) -> str:
        """
        Remove simple exact duplicated transcription.

        Example:
            Open node bar Open node bar

        becomes:

            Open node bar
        """

        words = text.split()

        if len(words) < 4:
            return text

        if len(words) % 2 != 0:
            return text

        midpoint = len(words) // 2

        first_half = words[:midpoint]
        second_half = words[midpoint:]

        if [
            word.lower() for word in first_half
        ] == [
            word.lower() for word in second_half
        ]:
            return " ".join(first_half)

        return text

    def _normalize_applications(
        self,
        text: str,
    ) -> tuple[str, list[str]]:
        """
        Replace explicit application-name aliases.

        Only the application phrase is changed.
        The rest of the user's sentence is preserved.
        """

        normalized = text
        corrections = []

        aliases = []

        for canonical, variants in self.APPLICATION_ALIASES.items():
            for variant in variants:
                aliases.append(
                    (
                        canonical,
                        variant,
                    )
                )

        aliases.sort(
            key=lambda item: len(item[1]),
            reverse=True,
        )

        for canonical, variant in aliases:
            pattern = re.compile(
                rf"(?<!\w){re.escape(variant)}(?!\w)",
                re.IGNORECASE,
            )

            match = pattern.search(normalized)

            if not match:
                continue

            matched_text = match.group(0)

            # Canonical name: normalize casing only.
            if matched_text.lower() == canonical.lower():
                normalized = pattern.sub(
                    canonical,
                    normalized,
                )
                continue

            normalized = pattern.sub(
                canonical,
                normalized,
            )

            corrections.append(
                f"{matched_text} -> {canonical}"
            )

        return normalized, corrections

    @staticmethod
    def _phonetic_key(text: str) -> str:
        """
        Produce a lightweight speech-oriented comparison key.

        This is NOT a full phonetic engine.

        It handles a few common English spelling/speech patterns
        that can appear in STT output.
        """

        value = text.lower().strip()

        # Remove separators that Whisper may introduce.
        value = re.sub(r"[\s\-_]+", "", value)

        # Common speech/spelling equivalences.
        replacements = [
            ("ough", "o"),
            ("augh", "a"),
            ("ph", "f"),
            ("th", "t"),
            ("ck", "k"),
            ("qu", "kw"),
            ("c", "k"),
        ]

        for source, target in replacements:
            value = value.replace(source, target)

        # Normalize a few commonly confused voiced/unvoiced
        # consonants for similarity comparison only.
        consonant_groups = {
            "b": "p",
            "d": "t",
            "g": "k",
            "v": "f",
            "z": "s",
        }

        value = "".join(
            consonant_groups.get(character, character)
            for character in value
        )

        return value

    def _application_similarity(
        self,
        spoken_target: str,
        canonical: str,
        aliases: list[str],
    ) -> float:
        """
        Calculate similarity using both normal and
        speech-oriented comparison.
        """

        spoken = spoken_target.lower().strip()

        candidates = [canonical] + aliases

        best_score = 0.0

        for candidate in candidates:
            normal_score = SequenceMatcher(
                None,
                spoken,
                candidate.lower(),
            ).ratio()

            spoken_key = self._phonetic_key(spoken)
            candidate_key = self._phonetic_key(candidate)

            phonetic_score = SequenceMatcher(
                None,
                spoken_key,
                candidate_key,
            ).ratio()

            score = max(
                normal_score,
                phonetic_score,
            )

            best_score = max(
                best_score,
                score,
            )

        return best_score

    def _high_confidence_fuzzy_app_correction(
        self,
        text: str,
    ) -> tuple[str, str | None]:
        """
        Apply fuzzy matching only to the application phrase
        immediately following an open/start/launch/run command.

        Multi-step commands are deliberately excluded.

        Example:

            Open NodePath
            -> Open notepad

        But:

            Open YouTube and search Telugu movies

        is left intact.
        """

        command_pattern = re.compile(
            r"^\s*(open|start|launch|run)\s+(.+?)\s*$",
            re.IGNORECASE,
        )

        match = command_pattern.match(text)

        if not match:
            return text, None

        command = match.group(1)
        target = match.group(2).strip()

        # Never fuzzy-correct a multi-step request.
        if re.search(
            r"\b(and|then|search|find|play|go to|navigate)\b",
            target,
            re.IGNORECASE,
        ):
            return text, None

        best_canonical = None
        best_score = 0.0

        for canonical, aliases in self.APPLICATION_ALIASES.items():
            score = self._application_similarity(
                spoken_target=target,
                canonical=canonical,
                aliases=aliases,
            )

            if score > best_score:
                best_score = score
                best_canonical = canonical

        # Very high threshold because false corrections are
        # worse than allowing AXE to reject an unknown command.
        if (
            best_canonical
            and best_score >= 0.84
            and target.lower() != best_canonical.lower()
        ):
            normalized = f"{command} {best_canonical}"

            return (
                normalized,
                f"{target} -> {best_canonical}",
            )

        return text, None


if __name__ == "__main__":
    normalizer = VoiceCommandNormalizer()

    examples = [
        "Open node bar",
        "Open node pad",
        "Open note pad",
        "Open NodePath",
        "Open Notepad",
        "Open node bar Open node bar",
        "Open YouTube and search Telugu movies",
        "Open YouTube and search Python tutorials",
        "YouTube open chesi Telugu movies search cheyyi",
        "Open Calculator",
        "Open cal culator",
    ]

    print("====================================")
    print("      VOICE NORMALIZER TEST")
    print("====================================")

    for example in examples:
        result = normalizer.normalize(example)

        print()
        print(f"Original:    {result['original_text']}")
        print(f"Normalized:  {result['normalized_text']}")
        print(f"Changed:     {result['changed']}")
        print(f"Corrections: {result['corrections']}")