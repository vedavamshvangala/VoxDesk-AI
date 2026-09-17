
import time

import numpy as np
import sounddevice as sd
from openwakeword.model import Model


SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1280
MICROPHONE_DEVICE = 1

THRESHOLD = 0.5


def main() -> None:
    print("====================================")
    print("      AXE WAKE ENGINE TEST")
    print("====================================")
    print()
    print("Model: Alexa")
    print(f"Threshold: {THRESHOLD}")
    print(f"Sample rate: {SAMPLE_RATE}")
    print(f"Chunk size: {CHUNK_SIZE}")
    print()
    print("Loading ONNX wake-word model...")

    model = Model(
        wakeword_models=[
            "alexa",
        ],
        inference_framework="onnx",
    )

    print("Model loaded successfully.")
    print()
    print("Listening...")
    print("Say: Alexa")
    print("Press Ctrl+C to stop.")
    print()

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            device=MICROPHONE_DEVICE,
        ) as stream:

            while True:
                audio, overflowed = stream.read(CHUNK_SIZE)

                if overflowed:
                    print(
                        "\nWarning: microphone buffer overflow."
                    )

                audio_data = np.asarray(
                    audio[:, 0],
                    dtype=np.int16,
                )

                prediction = model.predict(audio_data)

                score = prediction.get(
                    "alexa",
                    0.0,
                )

                print(
                    f"\rAlexa score: {score:.3f}",
                    end="",
                    flush=True,
                )

                if score >= THRESHOLD:
                    print()
                    print()
                    print("🔔 WAKE WORD DETECTED!")
                    print(f"Score: {score:.3f}")
                    print()

                    time.sleep(1.0)

    except KeyboardInterrupt:
        print()
        print()
        print("Wake engine stopped.")

    except Exception as exc:
        print()
        print()
        print(f"Wake engine error: {exc}")


if __name__ == "__main__":
    main()

