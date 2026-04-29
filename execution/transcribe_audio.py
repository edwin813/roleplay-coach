"""
Audio Transcription - Converts agent's speech to text using Deepgram.
"""
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

try:
    from deepgram import DeepgramClient, PrerecordedOptions, LiveOptions
except ImportError:
    DeepgramClient = None

load_dotenv()

def transcribe_audio_file(audio_file_path: str) -> Dict[str, Any]:
    """
    Transcribe an audio file to text using Deepgram.

    Args:
        audio_file_path: Path to audio file (wav, mp3, etc.)

    Returns:
        Dictionary with transcription results and metadata
    """
    if not DeepgramClient:
        return {
            "success": False,
            "error": "Deepgram SDK not installed. Run: pip install deepgram-sdk"
        }

    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "DEEPGRAM_API_KEY not found in .env file"
        }

    try:
        # Initialize Deepgram client
        deepgram = DeepgramClient(api_key)

        # Read audio file
        with open(audio_file_path, "rb") as audio:
            source = {"buffer": audio.read()}

        # Configure transcription options
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            punctuate=True,
            diarize=False,  # Single speaker
            language="en-US",
        )

        # Transcribe
        response = deepgram.listen.rest.v("1").transcribe_file(source, options)

        # Extract transcription
        transcript = response.results.channels[0].alternatives[0].transcript
        confidence = response.results.channels[0].alternatives[0].confidence
        words = response.results.channels[0].alternatives[0].words

        return {
            "success": True,
            "transcript": transcript,
            "confidence": confidence,
            "word_count": len(words),
            "duration": response.metadata.duration,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Transcription failed: {str(e)}"
        }

def transcribe_audio_stream(audio_data: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
    """
    Transcribe streaming audio data in real-time.

    Args:
        audio_data: Raw audio bytes
        sample_rate: Audio sample rate (default: 16000 Hz)

    Returns:
        Dictionary with transcription results
    """
    if not DeepgramClient:
        return {
            "success": False,
            "error": "Deepgram SDK not installed"
        }

    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "DEEPGRAM_API_KEY not found in .env"
        }

    try:
        deepgram = DeepgramClient(api_key)

        # For streaming, we'd use WebSocket connection
        # This is a simplified version for demonstration
        source = {"buffer": audio_data}

        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            punctuate=True,
            language="en-US",
        )

        response = deepgram.listen.rest.v("1").transcribe_file(source, options)
        transcript = response.results.channels[0].alternatives[0].transcript
        confidence = response.results.channels[0].alternatives[0].confidence

        return {
            "success": True,
            "transcript": transcript,
            "confidence": confidence,
            "is_final": True,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Stream transcription failed: {str(e)}"
        }

# Alternative: Use Web Speech API (browser-based, no cost)
def get_web_speech_config() -> Dict[str, Any]:
    """
    Returns configuration for browser-based Web Speech API.
    This is free but requires browser support.
    """
    return {
        "method": "browser",
        "api": "Web Speech API",
        "config": {
            "continuous": True,
            "interimResults": True,
            "language": "en-US",
            "maxAlternatives": 1
        },
        "cost": "Free (browser-based)",
        "note": "Fallback if Deepgram not available"
    }

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python transcribe_audio.py <audio_file_path>")
        print("\nOr get browser config:")
        print("python transcribe_audio.py --browser-config")
        sys.exit(1)

    if sys.argv[1] == "--browser-config":
        import json
        config = get_web_speech_config()
        print(json.dumps(config, indent=2))
    else:
        audio_path = sys.argv[1]
        result = transcribe_audio_file(audio_path)

        if result["success"]:
            print(f"✓ Transcription successful!")
            print(f"  Text: {result['transcript']}")
            print(f"  Confidence: {result['confidence']:.2%}")
            print(f"  Duration: {result['duration']:.2f}s")
        else:
            print(f"✗ Error: {result['error']}")
