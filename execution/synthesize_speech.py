"""
Speech Synthesis - Converts text to natural-sounding voice using Google TTS or ElevenLabs.
"""
import os
import logging
import traceback
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from text_filters import clean_text_for_speech

load_dotenv()

logger = logging.getLogger(__name__)

def synthesize_with_google(text: str, output_path: Optional[str] = None, voice_name: str = "en-US-Neural2-A") -> Dict[str, Any]:
    """
    Convert text to speech using Google Cloud Text-to-Speech.

    Args:
        text: Text to convert to speech
        output_path: Where to save audio file (default: .tmp/speech.mp3)
        voice_name: Google voice to use (default: Neural2-A - female)

    Returns:
        Dictionary with audio file path and metadata
    """
    # Safety filter: Remove any stage directions that slipped through
    text = clean_text_for_speech(text, log_changes=True)

    logger.info(f"🔊 Synthesizing speech with Google TTS: {text[:50]}...")

    try:
        from google.cloud import texttospeech
    except ImportError:
        error_msg = "Google Cloud TTS not installed. Run: pip install google-cloud-texttospeech"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

    # Use absolute path and always ensure directory exists
    if not output_path:
        output_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", ".tmp", "speech.mp3"
        ))
    else:
        # Convert relative paths to absolute
        output_path = os.path.abspath(output_path)

    logger.debug(f"Output path resolved to: {output_path}")

    # CRITICAL: Always ensure directory exists, even when path is provided
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        # Initialize client
        logger.debug("Initializing Google Cloud TTS client")
        client = texttospeech.TextToSpeechClient()

        # Set up synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Configure voice
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
        )

        # Configure audio output
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,  # Normal speed
            pitch=0.0,  # Normal pitch
        )

        # Perform synthesis
        logger.debug(f"Requesting synthesis with voice={voice_name}")
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # Save audio
        logger.debug(f"Writing audio to: {output_path}")
        with open(output_path, "wb") as out:
            out.write(response.audio_content)

        logger.info(f"✅ Audio synthesized successfully: {output_path}")
        return {
            "success": True,
            "audio_path": output_path,
            "text": text,
            "voice": voice_name,
            "provider": "Google Cloud TTS",
        }

    except Exception as e:
        logger.error(f"❌ Google TTS synthesis failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": f"Google TTS synthesis failed: {str(e)}"
        }

def synthesize_with_elevenlabs(text: str, output_path: Optional[str] = None, voice_id: str = "EXAVITQu4vr4xnSDxMaL") -> Dict[str, Any]:
    """
    Convert text to speech using ElevenLabs (more natural voices).

    Args:
        text: Text to convert
        output_path: Where to save audio
        voice_id: ElevenLabs voice ID (default: Sarah - friendly female)

    Returns:
        Dictionary with results
    """
    # Safety filter: Remove any stage directions that slipped through
    text = clean_text_for_speech(text, log_changes=True)

    logger.info(f"🔊 Synthesizing speech with ElevenLabs: {text[:50]}...")

    try:
        from elevenlabs.client import ElevenLabs
    except ImportError:
        error_msg = "ElevenLabs not installed. Run: pip install elevenlabs"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

    # Use absolute path and always ensure directory exists
    if not output_path:
        output_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", ".tmp", "speech.mp3"
        ))
    else:
        # Convert relative paths to absolute
        output_path = os.path.abspath(output_path)

    logger.debug(f"Output path resolved to: {output_path}")

    # CRITICAL: Always ensure directory exists, even when path is provided
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        error_msg = "ELEVENLABS_API_KEY not found in .env"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

    try:
        # Initialize client with API key
        client = ElevenLabs(api_key=api_key)
        logger.debug("ElevenLabs client initialized")

        # Generate speech using new API (using newer model for free tier)
        logger.debug(f"Requesting synthesis with voice_id={voice_id}, model=eleven_turbo_v2")
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_turbo_v2"  # Free tier compatible model
        )

        # Save audio - audio is an iterator of bytes
        logger.debug(f"Writing audio to: {output_path}")
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)

        logger.info(f"✅ Audio synthesized successfully: {output_path}")
        return {
            "success": True,
            "audio_path": output_path,
            "text": text,
            "voice_id": voice_id,
            "provider": "ElevenLabs",
        }

    except Exception as e:
        logger.error(f"❌ ElevenLabs synthesis failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": f"ElevenLabs synthesis failed: {str(e)}"
        }

def synthesize_speech(text: str, output_path: Optional[str] = None, provider: str = "elevenlabs") -> Dict[str, Any]:
    """
    Convert text to speech using preferred provider.

    Args:
        text: Text to synthesize
        output_path: Output file path
        provider: "google" or "elevenlabs"

    Returns:
        Dictionary with results
    """
    if provider == "elevenlabs":
        return synthesize_with_elevenlabs(text, output_path)
    else:
        return synthesize_with_google(text, output_path)

# Voice options for variety
VOICE_PROFILES = {
    "google": {
        "female_friendly": "en-US-Neural2-A",
        "female_professional": "en-US-Neural2-C",
        "male_friendly": "en-US-Neural2-D",
        "male_professional": "en-US-Neural2-I",
    },
    "elevenlabs": {
        "sarah_friendly": "EXAVITQu4vr4xnSDxMaL",
        "rachel_calm": "21m00Tcm4TlvDq8ikWAM",
        "adam_deep": "pNInz6obpgDQGcFmaJgB",
        "antoni_smooth": "ErXwobaYiN019PkySvjV",
    }
}

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python synthesize_speech.py \"<text>\" [google|elevenlabs]")
        print("\nAvailable voices:")
        print("Google:", list(VOICE_PROFILES["google"].keys()))
        print("ElevenLabs:", list(VOICE_PROFILES["elevenlabs"].keys()))
        sys.exit(1)

    text = sys.argv[1]
    provider = sys.argv[2] if len(sys.argv) > 2 else "google"

    result = synthesize_speech(text, provider=provider)

    if result["success"]:
        print(f"✓ Speech synthesized successfully!")
        print(f"  Audio saved to: {result['audio_path']}")
        print(f"  Provider: {result['provider']}")
        print(f"  Text: {result['text']}")
    else:
        print(f"✗ Error: {result['error']}")
