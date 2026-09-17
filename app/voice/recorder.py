import wave
from pathlib import Path

import sounddevice as sd


SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2
MICROPHONE_DEVICE = 1


def record_audio(
    output_path: str | Path = "recording.wav",
    duration: int = 5,
) -> dict:
    """
    Record audio from the configured microphone and save it as WAV.
    """

    if duration <= 0:
        return {
            "success": False,
            "message": "Recording duration must be greater than zero.",
            "path": None,
        }

    output_path = Path(output_path)

    try:
        device_info = sd.query_devices(MICROPHONE_DEVICE)

        print(f"Microphone: {device_info['name']}")
        print(f"Recording for {duration} seconds...")
        print("Speak now...")

        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            device=MICROPHONE_DEVICE,
        )

        sd.wait()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(SAMPLE_WIDTH)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(audio.tobytes())

        print(f"Recording saved: {output_path}")

        return {
            "success": True,
            "message": "Audio recorded successfully.",
            "path": str(output_path),
            "duration": duration,
            "sample_rate": SAMPLE_RATE,
            "channels": CHANNELS,
            "device": device_info["name"],
        }

    except Exception as exc:
        return {
            "success": False,
            "message": f"Microphone recording failed: {exc}",
            "path": None,
        }


if __name__ == "__main__":
    result = record_audio(
        output_path="recording.wav",
        duration=5,
    )

    print(result)