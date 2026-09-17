
from pathlib import Path
from typing import Any

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

    def process_voice_command(self) -> dict[str, Any]:
        """
        Wait for Alexa, then process one voice command through
        STT, normalization, AXE, and TTS.
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

        raw_text = voice_input.get("raw_text", "").strip()
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

        return {
            **voice_input,
            "success": True,
            "text": normalized_text,
            "wake_result": wake_result,
            "axe_response": response,
            "tts_result": tts_result,
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
    print(f"Wake word:    {result.get('wake_result', {})}")
    print(f"Raw STT:      {result.get('raw_text', '')}")
    print(f"AXE Input:    {result.get('normalized_text', '')}")
    print(f"AXE Response: {result.get('axe_response', '')}")
    print(f"TTS Result:   {result.get('tts_result', {})}")
    print(f"Status:       {result.get('success')}")

