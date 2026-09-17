
from pathlib import Path
from typing import Any
import re

from app.core.agent import AXE
from app.voice.normalizer import VoiceCommandNormalizer
from app.voice.recorder import record_audio
from app.voice.stt import GroqSTT
from app.voice.tts import WindowsTTS
from app.voice.wake_word import AXEWakeWordDetector


class VoiceAssistant:
    def __init__(
        self,
        audio_path: str | Path = "recording.wav",
        recording_duration: int = 5,
        wake_threshold: float = 0.5,
    ) -> None:
        self.audio_path = Path(audio_path)
        self.recording_duration = recording_duration

        self.axe = AXE()
        self.stt = GroqSTT()
        self.normalizer = VoiceCommandNormalizer()

        self.tts = WindowsTTS(
            voice_name="Microsoft David",
            rate=150,
            volume=1.0,
        )

        self.wake_detector = AXEWakeWordDetector(
            threshold=wake_threshold,
        )

    def listen(self) -> dict[str, Any]:
        """Record one command, transcribe it, and normalize it."""

        recording = record_audio(
            output_path=self.audio_path,
            duration=self.recording_duration,
        )

        if not recording.get("success"):
            return {
                "success": False,
                "text": "",
                "raw_text": "",
                "normalized_text": "",
                "message": recording.get(
                    "message",
                    "Audio recording failed.",
                ),
                "recording": recording,
                "transcription": None,
                "normalization": None,
            }

        transcription = self.stt.transcribe(
            audio_path=self.audio_path,
        )

        if not transcription.get("success"):
            return {
                "success": False,
                "text": "",
                "raw_text": "",
                "normalized_text": "",
                "message": transcription.get(
                    "message",
                    "Speech transcription failed.",
                ),
                "recording": recording,
                "transcription": transcription,
                "normalization": None,
            }

        raw_text = transcription.get("text", "").strip()

        if not raw_text:
            return {
                "success": False,
                "text": "",
                "raw_text": "",
                "normalized_text": "",
                "message": "No speech was detected.",
                "recording": recording,
                "transcription": transcription,
                "normalization": None,
            }

        normalization = self.normalizer.normalize(raw_text)

        if not normalization.get("success"):
            return {
                "success": False,
                "text": raw_text,
                "raw_text": raw_text,
                "normalized_text": raw_text,
                "message": normalization.get(
                    "message",
                    "Voice command normalization failed.",
                ),
                "recording": recording,
                "transcription": transcription,
                "normalization": normalization,
            }

        normalized_text = normalization.get(
            "normalized_text",
            raw_text,
        ).strip()

        return {
            "success": True,
            "text": normalized_text,
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "message": "Voice input processed successfully.",
            "recording": recording,
            "transcription": transcription,
            "normalization": normalization,
        }

    def wait_for_wake_word(self) -> dict[str, Any]:
        """Wait until the Alexa wake word is detected."""

        print()
        print("====================================")
        print("          AXE IS LISTENING")
        print("====================================")
        print("Say: Alexa")
        print()

        return self.wake_detector.wait_for_wake_word()

    def speak(self, text: str) -> dict[str, Any]:
        """Speak AXE's response using Windows TTS."""

        if not text or not text.strip():
            return {
                "success": False,
                "message": "No response text was provided for speech.",
                "text": text,
            }

        print("AXE: Speaking response...")

        result = self.tts.speak_response(text.strip())

        if result.get("success"):
            print("AXE: Speech played successfully.")
        else:
            print(
                "AXE: Speech playback failed: "
                f"{result.get('message', 'Unknown error.')}"
            )

        return result

    def _normalize_approval_response(self, text: str) -> str:
        """
        Normalize spoken approval/rejection responses so AXE can
        recognize common STT punctuation and natural wording.

        Examples:

            "Yes."          -> "yes"
            "YES!"          -> "yes"
            "Yes, please."  -> "yes"
            "Yes go ahead"  -> "yes"
            "No."           -> "no"
            "No, cancel it" -> "no"
        """

        value = text.strip().lower()

        # Remove common punctuation introduced by STT.
        value = re.sub(r"[.!?,;:]+", " ", value)

        # Normalize whitespace.
        value = re.sub(r"\s+", " ", value).strip()

        # Direct approval responses.
        positive_exact = {
            "yes",
            "y",
            "yeah",
            "yep",
            "yup",
            "sure",
            "okay",
            "ok",
            "alright",
            "all right",
            "go ahead",
            "do it",
            "continue",
            "proceed",
            "approve",
            "approved",
        }

        # Direct rejection responses.
        negative_exact = {
            "no",
            "n",
            "nope",
            "nah",
            "cancel",
            "stop",
            "reject",
            "rejected",
            "dont",
            "don't",
            "do not",
        }

        if value in positive_exact:
            return "yes"

        if value in negative_exact:
            return "no"

        # Handle common natural spoken approval phrases.
        positive_prefixes = (
            "yes ",
            "yeah ",
            "yep ",
            "yup ",
            "sure ",
            "okay ",
            "ok ",
            "go ahead ",
            "do it ",
            "continue ",
            "proceed ",
            "approve ",
        )

        negative_prefixes = (
            "no ",
            "nope ",
            "nah ",
            "cancel ",
            "stop ",
            "reject ",
            "don't ",
            "dont ",
            "do not ",
        )

        if value.startswith(positive_prefixes):
            return "yes"

        if value.startswith(negative_prefixes):
            return "no"

        # If the response contains a very clear approval phrase,
        # treat it as approval.
        positive_phrases = (
            "yes please",
            "yes go ahead",
            "yes continue",
            "yes do it",
            "please continue",
            "please proceed",
        )

        negative_phrases = (
            "no please",
            "no cancel",
            "no stop",
            "don't continue",
            "do not continue",
        )

        if value in positive_phrases:
            return "yes"

        if value in negative_phrases:
            return "no"

        # Return the cleaned value if it is not recognized.
        # AXE will then safely keep the task pending.
        return value

    def _listen_for_approval(self) -> dict[str, Any]:
        """
        Listen specifically for the user's response to an AXE
        approval request.

        The Alexa wake word is NOT required here.

        The user can simply say:
            Yes
        or:
            No
        """

        print()
        print("====================================")
        print("       AXE APPROVAL REQUIRED")
        print("====================================")
        print("Listening for approval...")
        print("Say: Yes or No")
        print()

        approval_input = self.listen()

        if not approval_input.get("success"):
            return {
                "success": False,
                "approved": None,
                "response": "",
                "input": approval_input,
                "message": approval_input.get(
                    "message",
                    "Could not capture your approval response.",
                ),
            }

        raw_approval_text = approval_input.get(
            "normalized_text",
            "",
        ).strip()

        print(
            f"Approval response received: "
            f"{raw_approval_text}"
        )

        if not raw_approval_text:
            return {
                "success": False,
                "approved": None,
                "response": "",
                "input": approval_input,
                "message": "No approval response was detected.",
            }

        # IMPORTANT:
        # Whisper returned "Yes." in the failing test.
        # Convert it to "yes" before sending it to AXE.
        approval_text = self._normalize_approval_response(
            raw_approval_text
        )

        print(
            f"Approval response normalized: "
            f"{approval_text}"
        )

        # Send the normalized approval directly to AXE.
        #
        # AXE already owns the pending task and will:
        #
        #   yes -> execute pending task
        #   no  -> cancel pending task
        #
        response = self.axe.respond(approval_text)

        print(f"AXE approval response: {response}")

        approved = approval_text == "yes"
        rejected = approval_text == "no"

        return {
            "success": True,
            "approved": approved if approved or rejected else None,
            "response": response,
            "input": approval_input,
            "normalized_approval": approval_text,
            "message": "Approval response processed by AXE.",
        }

    def process_voice_command(self) -> dict[str, Any]:
        """
        Wait for Alexa, process one voice command through STT,
        normalization, AXE, and TTS.

        If AXE requests human approval, immediately enter a
        dedicated approval-listening state without requiring
        the Alexa wake word again.
        """

        wake_result = self.wait_for_wake_word()

        if not wake_result.get("success"):
            return {
                "success": False,
                "text": "",
                "raw_text": "",
                "normalized_text": "",
                "axe_response": "",
                "tts_result": None,
                "wake_result": wake_result,
                "message": wake_result.get(
                    "message",
                    "Wake-word detection failed.",
                ),
            }

        if not wake_result.get("wake_detected"):
            return {
                "success": False,
                "text": "",
                "raw_text": "",
                "normalized_text": "",
                "axe_response": "",
                "tts_result": None,
                "wake_result": wake_result,
                "message": "Alexa wake word was not detected.",
            }

        print()
        print("Wake word detected.")
        print("Now listening for your command...")
        print()

        voice_input = self.listen()

        if not voice_input.get("success"):
            return {
                **voice_input,
                "wake_result": wake_result,
                "axe_response": "",
                "tts_result": None,
            }

        raw_text = voice_input.get(
            "raw_text",
            "",
        ).strip()

        normalized_text = voice_input.get(
            "normalized_text",
            "",
        ).strip()

        if not normalized_text:
            return {
                **voice_input,
                "success": False,
                "wake_result": wake_result,
                "axe_response": "",
                "tts_result": None,
                "message": "No usable voice command was detected.",
            }

        print(f"You said: {raw_text}")

        if raw_text.lower() != normalized_text.lower():
            print(f"AXE input: {normalized_text}")

        response = self.axe.respond(normalized_text)

        print(f"AXE response: {response}")

        tts_result = self.speak(response)

        # ---------------------------------------------------------
        # HUMAN APPROVAL FLOW
        # ---------------------------------------------------------
        #
        # If AXE has stored a pending task, the previous command
        # requires human approval.
        #
        # We now listen directly for "yes" or "no".
        #
        # No Alexa wake word is required here.
        # ---------------------------------------------------------

        approval_result = None
        approval_tts_result = None

        if self.axe.pending_task is not None:
            print()
            print("AXE is waiting for your approval.")
            print(
                "The next voice input will be treated "
                "as approval."
            )
            print()

            approval_result = self._listen_for_approval()

            if approval_result.get("success"):
                approval_response = approval_result.get(
                    "response",
                    "",
                )

                if approval_response:
                    approval_tts_result = self.speak(
                        approval_response
                    )

                response = approval_response

            else:
                print(
                    "AXE approval listening failed: "
                    f"{approval_result.get('message', 'Unknown error.')}"
                )

                approval_message = (
                    "I could not hear your approval response. "
                    "Please try the command again."
                )

                approval_tts_result = self.speak(
                    approval_message
                )

                response = approval_message

        return {
            **voice_input,
            "success": True,
            "text": normalized_text,
            "wake_result": wake_result,
            "axe_response": response,
            "tts_result": tts_result,
            "approval_result": approval_result,
            "approval_tts_result": approval_tts_result,
            "message": "Voice command processed by AXE.",
        }


if __name__ == "__main__":
    assistant = VoiceAssistant(
        audio_path="recording.wav",
        recording_duration=5,
        wake_threshold=0.5,
    )

    result = assistant.process_voice_command()

    print()
    print("====================================")
    print("           VOICE RESULT")
    print("====================================")
    print(f"Wake word:          {result.get('wake_result', {})}")
    print(f"Raw STT:            {result.get('raw_text', '')}")
    print(f"AXE Input:          {result.get('normalized_text', '')}")
    print(f"AXE Response:       {result.get('axe_response', '')}")
    print(f"TTS Result:         {result.get('tts_result', {})}")
    print(
        f"Approval Result:    "
        f"{result.get('approval_result', {})}"
    )
    print(
        f"Approval TTS:       "
        f"{result.get('approval_tts_result', {})}"
    )
    print(f"Status:             {result.get('success')}")

