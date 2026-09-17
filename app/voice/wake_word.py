from typing import Any

import numpy as np
import sounddevice as sd
from openwakeword.model import Model


SAMPLE_RATE = 16000
CHANNELS = 1

# Microphone already verified successfully.
MICROPHONE_DEVICE = 1

# openWakeWord streaming chunk size.
CHUNK_SIZE = 1280

# Alexa detection threshold.
THRESHOLD = 0.5

WAKE_WORD = "alexa"


class AXEWakeWordDetector:
    """
    Local continuous wake-word detector for AXE.

    Wake word:
        Alexa

    Audio processing:
        Microphone -> openWakeWord -> Alexa score

    Wake-word detection is performed locally.
    """

    def __init__(
        self,
        microphone_device: int = MICROPHONE_DEVICE,
        threshold: float = THRESHOLD,
    ) -> None:
        self.microphone_device = microphone_device
        self.threshold = threshold

        try:
            # Let openWakeWord resolve the installed model.
            # The model was downloaded using:
            # openwakeword.utils.download_models()
            self.model = Model(
                wakeword_models=[WAKE_WORD],
                inference_framework="onnx",
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialize openWakeWord Alexa model: {exc}"
            ) from exc

        if WAKE_WORD not in self.model.models:
            raise RuntimeError(
                "Alexa wake-word model was not loaded correctly. "
                f"Available models: {list(self.model.models.keys())}"
            )

    def detect_once(
        self,
        max_duration: float | None = None,
    ) -> dict[str, Any]:
        """
        Listen continuously and detect the Alexa wake word.

        Args:
            max_duration:
                Maximum listening duration in seconds.
                None means continuous listening.

        Returns:
            Dictionary containing detection status and score.
        """

        if max_duration is not None and max_duration <= 0:
            return {
                "success": False,
                "wake_detected": False,
                "wake_word": WAKE_WORD,
                "score": 0.0,
                "message": (
                    "Maximum listening duration must be "
                    "greater than zero."
                ),
            }

        try:
            device_info = sd.query_devices(
                self.microphone_device
            )

            print()
            print("====================================")
            print("       AXE WAKE-WORD DETECTOR")
            print("====================================")
            print()
            print(f"Microphone : {device_info['name']}")
            print(f"Device     : {self.microphone_device}")
            print(f"Wake word  : {WAKE_WORD}")
            print(f"Threshold  : {self.threshold}")
            print(f"Sample rate: {SAMPLE_RATE}")
            print(f"Chunk size : {CHUNK_SIZE}")
            print()
            print("Listening for wake word...")
            print("Say: Alexa")
            print("Press Ctrl+C to stop.")
            print()

            elapsed_samples = 0

            max_samples = (
                int(max_duration * SAMPLE_RATE)
                if max_duration is not None
                else None
            )

            # Create a fresh model state for every detection session.
            self.model.reset()

            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                device=self.microphone_device,
            ) as stream:

                while True:
                    audio, overflowed = stream.read(
                        CHUNK_SIZE
                    )

                    if overflowed:
                        print(
                            "\nWarning: microphone buffer overflow."
                        )

                    audio_array = np.asarray(
                        audio,
                        dtype=np.int16,
                    )

                    if audio_array.ndim == 2:
                        audio_data = audio_array[:, 0]
                    else:
                        audio_data = audio_array

                    prediction = self.model.predict(
                        audio_data
                    )

                    score = float(
                        prediction.get(
                            WAKE_WORD,
                            0.0,
                        )
                    )

                    print(
                        f"\rAlexa score: {score:.3f}",
                        end="",
                        flush=True,
                    )

                    elapsed_samples += len(audio_data)

                    if score >= self.threshold:
                        print()
                        print()
                        print("====================================")
                        print("       WAKE WORD DETECTED")
                        print("====================================")
                        print()
                        print(f"Wake word: {WAKE_WORD}")
                        print(f"Score    : {score:.3f}")
                        print()

                        return {
                            "success": True,
                            "wake_detected": True,
                            "wake_word": WAKE_WORD,
                            "score": score,
                            "message": (
                                "Alexa wake word detected."
                            ),
                        }

                    if (
                        max_samples is not None
                        and elapsed_samples >= max_samples
                    ):
                        print()
                        print()

                        return {
                            "success": True,
                            "wake_detected": False,
                            "wake_word": WAKE_WORD,
                            "score": score,
                            "message": (
                                "Wake word was not detected "
                                "within the listening duration."
                            ),
                        }

        except KeyboardInterrupt:
            print()
            print()
            print("Wake-word detector stopped by user.")

            return {
                "success": False,
                "wake_detected": False,
                "wake_word": WAKE_WORD,
                "score": 0.0,
                "message": (
                    "Wake-word detector stopped by user."
                ),
            }

        except Exception as exc:
            print()
            print()
            print(
                f"Wake-word detection failed: {exc}"
            )

            return {
                "success": False,
                "wake_detected": False,
                "wake_word": WAKE_WORD,
                "score": 0.0,
                "message": (
                    f"Wake-word detection failed: {exc}"
                ),
            }

    def wait_for_wake_word(self) -> dict[str, Any]:
        """
        Continuously wait until Alexa is detected.
        """

        return self.detect_once()

    def is_wake_word(
        self,
        text: str,
    ) -> bool:
        """
        Text-based wake-word helper.

        This does not perform microphone detection.
        """

        if not isinstance(text, str):
            return False

        normalized = " ".join(
            text.lower().strip().split()
        )

        return normalized == WAKE_WORD


if __name__ == "__main__":
    print("====================================")
    print("       AXE WAKE-WORD TEST")
    print("====================================")
    print()

    print(f"Wake word  : {WAKE_WORD}")
    print(f"Threshold  : {THRESHOLD}")
    print(f"Sample rate: {SAMPLE_RATE}")
    print(f"Chunk size : {CHUNK_SIZE}")
    print(f"Microphone : {MICROPHONE_DEVICE}")
    print()

    try:
        detector = AXEWakeWordDetector()

        print("Alexa model loaded successfully.")
        print(
            f"Loaded models: "
            f"{list(detector.model.models.keys())}"
        )
        print()

        print("Text matching tests:")
        print(
            f"'Alexa' -> "
            f"{detector.is_wake_word('Alexa')}"
        )
        print(
            f"'alex' -> "
            f"{detector.is_wake_word('alex')}"
        )
        print(
            f"'Open Notepad' -> "
            f"{detector.is_wake_word('Open Notepad')}"
        )

        print()
        print("Starting live wake-word detection...")
        print()

        result = detector.wait_for_wake_word()

        print()
        print("====================================")
        print("         WAKE-WORD RESULT")
        print("====================================")
        print()
        print(result)

    except Exception as exc:
        print()
        print(
            f"Wake-word initialization failed: {exc}"
        )
