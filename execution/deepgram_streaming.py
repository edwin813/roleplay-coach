"""
Deepgram Live Streaming - Real-time audio transcription with Voice Activity Detection.

This module provides a LiveTranscriber class using Deepgram SDK v5.x for:
1. WebSocket connection to Deepgram's live streaming API
2. Real-time transcription with interim results
3. Built-in Voice Activity Detection (VAD) for speech end detection
4. Event-driven architecture for transcript callbacks
"""

import os
import asyncio
from typing import Callable, Optional
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.extensions.types.sockets import ListenV1ControlMessage
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveTranscriber:
    """
    Manages a live transcription session with Deepgram WebSocket API v5.x.

    Usage:
        transcriber = LiveTranscriber(
            on_transcript=handle_transcript,
            on_speech_final=handle_speech_end
        )
        await transcriber.start()
        transcriber.send_audio(audio_chunk)
        await transcriber.stop()
    """

    def __init__(
        self,
        on_transcript: Optional[Callable[[str, bool], None]] = None,
        on_speech_final: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the live transcriber.

        Args:
            on_transcript: Callback for interim/final transcripts (text, is_final)
            on_speech_final: Callback when speech is confidently finished (text)
            on_error: Callback for errors (error_message)
        """
        self.api_key = os.getenv('DEEPGRAM_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY not found in environment")

        self.client = AsyncDeepgramClient(api_key=self.api_key)
        self.socket = None
        self.is_connected = False
        self.listen_task = None
        self._connection_context = None

        # Callbacks
        self.on_transcript = on_transcript
        self.on_speech_final = on_speech_final
        self.on_error = on_error

        # Transcription buffer
        self.current_transcript = ""
        self.last_final_transcript = ""

        # Connection tracking for monitoring
        self.connection_id = None
        self.start_time = None
        self.connection_attempts = 0

        # NEW: Full utterance accumulator with state tracking
        self.utterance_accumulator = ""
        self.utterance_state = "IDLE"  # IDLE, ACCUMULATING, FINALIZING
        self.seen_chunks = set()  # For deduplication
        self.accumulation_start_time = None

    async def start(self):
        """Start the Deepgram live transcription session."""
        import uuid
        import time

        self.connection_id = str(uuid.uuid4())[:8]
        self.start_time = time.time()
        self.connection_attempts += 1

        logger.info(f"🔌 [Connection {self.connection_id}] Starting Deepgram connection (attempt #{self.connection_attempts})")

        # Ensure accumulator is clean on new session
        self._reset_accumulator()

        try:
            # Create WebSocket connection with options
            # Let Deepgram auto-detect audio format (supports WebM/Opus)
            logger.info(f"🔌 [Connection {self.connection_id}] Creating WebSocket connection...")
            connection = self.client.listen.v1.connect(
                model="nova-2",
                interim_results="true",
                vad_events="true",
                endpointing="500",   # 500ms silence = end of speech (allows natural pauses, prevents mid-sentence cutoffs)
                punctuate="true",
                smart_format="true",
            )

            # Enter the async context manager to get the socket
            logger.info(f"🔌 [Connection {self.connection_id}] Entering context manager...")
            self.socket = await connection.__aenter__()
            self._connection_context = connection

            logger.info(f"🔌 [Connection {self.connection_id}] Registering event handlers...")
            # Register event handlers
            self.socket.on(EventType.OPEN, self._handle_open)
            self.socket.on(EventType.MESSAGE, self._handle_message)
            self.socket.on(EventType.ERROR, self._handle_error)
            self.socket.on(EventType.CLOSE, self._handle_close)

            logger.info(f"🔌 [Connection {self.connection_id}] Starting background listener...")
            # Start listening in background task
            self.listen_task = asyncio.create_task(self.socket.start_listening())

            self.is_connected = True
            elapsed = time.time() - self.start_time
            logger.info(f"✅ [Connection {self.connection_id}] Deepgram live transcription started in {elapsed:.2f}s")
            return True

        except Exception as e:
            elapsed = time.time() - self.start_time if self.start_time else 0
            logger.error(f"❌ [Connection {self.connection_id}] Error starting transcription after {elapsed:.2f}s: {type(e).__name__}: {str(e)}")
            if self.on_error:
                self.on_error(str(e))
            return False

    def send_audio(self, audio_chunk: bytes, event_loop=None):
        """
        Send audio chunk to Deepgram for transcription.

        Args:
            audio_chunk: Raw audio data (PCM, WebM, Opus, etc.)
            event_loop: Event loop to run the async operation in (optional)
        """
        if not self.is_connected or not self.socket:
            logger.warning("⚠️ Not connected, cannot send audio")
            return False

        try:
            # If no event loop provided, try to get the running one
            if event_loop is None:
                try:
                    event_loop = asyncio.get_running_loop()
                except RuntimeError:
                    # No running loop in this thread, socket will handle it
                    # Just call the coroutine directly (socket.send_media is designed for this)
                    pass

            if event_loop:
                # Schedule in the provided event loop
                future = asyncio.run_coroutine_threadsafe(
                    self._async_send_audio(audio_chunk),
                    event_loop
                )
                # Surface async errors instead of swallowing them
                def _on_send_done(f):
                    if not f.cancelled():
                        exc = f.exception()
                        if exc:
                            logger.error(f"❌ Async send_audio failed: {exc}")
                future.add_done_callback(_on_send_done)
            else:
                # Fallback: try direct call (some SDK versions support this)
                try:
                    # Try creating a task if we can get a loop
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(self._async_send_audio(audio_chunk))
                    loop.close()
                except Exception:
                    # Last resort: the socket might handle sync calls
                    pass

            return True
        except Exception as e:
            logger.error(f"❌ Error sending audio: {str(e)}")
            return False

    async def _async_send_audio(self, audio_chunk: bytes):
        """Async helper to send audio."""
        try:
            await self.socket.send_media(audio_chunk)
        except Exception as e:
            logger.error(f"❌ Error in _async_send_audio: {str(e)}")

    async def stop(self):
        """Stop the Deepgram live transcription session with thorough cleanup."""
        if not self.is_connected:
            logger.info("🛑 Transcription already stopped")
            return

        try:
            # Mark as disconnected first to prevent new audio sends
            self.is_connected = False

            # Send finalize to get any remaining results (async)
            try:
                await self.socket.send_control(ListenV1ControlMessage(type="Finalize"))
            except Exception as e:
                logger.warning(f"⚠️ Could not send finalize: {e}")

            # Cancel background listening task
            if self.listen_task and not self.listen_task.done():
                self.listen_task.cancel()
                try:
                    await asyncio.wait_for(self.listen_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.info("🔌 Listen task cancelled")
                except Exception as e:
                    logger.warning(f"⚠️ Error cancelling listen task: {e}")

            # Close WebSocket connection
            if self._connection_context:
                try:
                    await asyncio.wait_for(
                        self._connection_context.__aexit__(None, None, None),
                        timeout=3.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Connection cleanup timed out")
                except Exception as e:
                    logger.warning(f"⚠️ Error during connection cleanup: {e}")

                self._connection_context = None

            # Clear socket reference
            self.socket = None

            # Small delay to ensure Deepgram server processes the disconnect
            await asyncio.sleep(0.1)

            # Reset accumulator when stopping
            self._reset_accumulator()

            logger.info("✅ Deepgram transcription stopped and cleaned up")

        except Exception as e:
            logger.error(f"❌ Error stopping transcription: {str(e)}")
            # Force cleanup even if errors occurred
            self.is_connected = False
            self.socket = None
            self._connection_context = None

    def _reset_accumulator(self):
        """Reset utterance accumulator for next speech."""
        self.utterance_accumulator = ""
        self.utterance_state = "IDLE"
        self.seen_chunks.clear()
        self.accumulation_start_time = None
        self.last_final_transcript = ""
        self.current_transcript = ""
        logger.debug(f"🔄 Accumulator reset")

    def _handle_open(self, event):
        """Handle WebSocket connection open."""
        logger.info("🔌 Deepgram WebSocket connected")

    def _handle_message(self, message):
        """
        Handle transcript results from Deepgram.

        Deepgram sends different message types:
        - Results: Transcription results (interim or final)
        - SpeechStarted: Speech detected
        - UtteranceEnd: Utterance complete
        - Metadata: Connection information
        """
        try:
            msg_type = getattr(message, 'type', None)

            if msg_type == "Results":
                # Extract transcript
                if not hasattr(message, 'channel') or not message.channel.alternatives:
                    return

                transcript = message.channel.alternatives[0].transcript

                # Skip empty transcripts
                if not transcript or transcript.strip() == "":
                    return

                is_final = getattr(message, 'is_final', False)
                speech_final = getattr(message, 'speech_final', False)

                logger.info(f"📝 Transcript: '{transcript}' (final={is_final}, speech_final={speech_final})")

                # Update state machine
                import time
                if self.utterance_state == "IDLE" and transcript.strip():
                    self.utterance_state = "ACCUMULATING"
                    self.accumulation_start_time = time.time()
                    logger.info(f"🎙️ Started accumulating utterance")

                # FIXED: Smart accumulation logic - only accumulate FINAL chunks
                if self.utterance_state == "ACCUMULATING":
                    # Only accumulate FINAL chunks (confirmed text)
                    if is_final and transcript.strip():
                        # Append final chunks to accumulator
                        if self.utterance_accumulator:
                            # Check if it's new content (not already in accumulator)
                            if not self.utterance_accumulator.endswith(transcript):
                                # Smart concatenation: check if there's overlap
                                words_acc = self.utterance_accumulator.split()
                                words_new = transcript.split()

                                # If last words of accumulator match first words of new, merge
                                overlap_found = False
                                for i in range(min(3, len(words_new))):  # Check up to 3 words
                                    if len(words_acc) > i and words_acc[-i-1:] == words_new[:i+1]:
                                        # Overlap found, append only the new part
                                        self.utterance_accumulator += " " + " ".join(words_new[i+1:])
                                        overlap_found = True
                                        break

                                if not overlap_found:
                                    # No overlap, just append with space
                                    self.utterance_accumulator += " " + transcript
                        else:
                            self.utterance_accumulator = transcript

                        logger.debug(f"📝 Added final chunk. Accumulator: '{self.utterance_accumulator[:80]}...'")

                    # Interim results don't go in accumulator, but we track the last one
                    # (it will be used to fill gaps at speech_final)

                # Store in old buffers for backward compatibility
                if is_final:
                    self.last_final_transcript = transcript
                    self.current_transcript = ""
                else:
                    self.current_transcript = transcript

                # Call transcript callback
                if self.on_transcript:
                    self.on_transcript(transcript, is_final)

                # Speech finalization - FIXED: Combine accumulator + last interim
                if speech_final and self.on_speech_final:
                    self.utterance_state = "FINALIZING"

                    # Combine accumulated final chunks with last interim result
                    final_from_accumulator = self.utterance_accumulator.strip()
                    final_from_interim = self.current_transcript.strip()

                    # Use whichever is longer (or combine if different)
                    if len(final_from_interim) > len(final_from_accumulator):
                        final_text = final_from_interim
                        logger.info(f"🎤 Using interim (longer): '{final_text[:50]}...'")
                    elif final_from_accumulator:
                        # Check if interim adds anything new
                        if final_from_interim and final_from_interim not in final_from_accumulator:
                            final_text = final_from_accumulator + " " + final_from_interim
                            logger.info(f"🎤 Combined accumulator + interim: '{final_text[:50]}...'")
                        else:
                            final_text = final_from_accumulator
                            logger.info(f"🎤 Using accumulator: '{final_text[:50]}...'")
                    else:
                        final_text = final_from_interim
                        logger.info(f"🎤 Using interim (accumulator empty): '{final_text[:50]}...'")

                    if final_text:
                        elapsed = time.time() - self.accumulation_start_time if self.accumulation_start_time else 0
                        logger.info(f"✅ Speech final complete: '{final_text}' ({elapsed:.1f}s)")
                        logger.info(f"   Accumulator had: '{final_from_accumulator[:50]}...'")
                        logger.info(f"   Last interim had: '{final_from_interim[:50]}...'")
                        self.on_speech_final(final_text)

                    # Reset accumulator after finalizing
                    self._reset_accumulator()

            elif msg_type == "SpeechStarted":
                logger.info("🎤 Speech detected")

            elif msg_type == "UtteranceEnd":
                logger.info("🎤 Utterance ended")

            elif msg_type == "Metadata":
                logger.info(f"📊 Metadata: request_id={getattr(message, 'request_id', 'unknown')}")

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")

    def _handle_error(self, error):
        """Handle Deepgram errors."""
        logger.error(f"❌ Deepgram error: {error}")
        if self.on_error:
            self.on_error(str(error))

    def _handle_close(self, event):
        """Handle connection close."""
        logger.info(f"🔌 Deepgram connection closed")
        self.is_connected = False


class TranscriptionSession:
    """
    Higher-level session manager that coordinates transcription with conversation flow.

    This handles the state machine:
    - IDLE: Not transcribing
    - LISTENING: Actively transcribing agent speech
    - AI_SPEAKING: AI is talking, transcription paused
    - PROCESSING: Speech detected, processing response
    """

    def __init__(self, session_id: str, event_loop=None):
        self.session_id = session_id
        self.transcriber = None
        self.state = "IDLE"
        self.event_loop = event_loop

        # Transcription accumulator
        self.interim_transcript = ""
        self.final_transcript = ""

        # Callbacks (set by server)
        self.on_agent_speech_complete = None
        self.on_interim_update = None

    async def start_listening(self):
        """Start listening for agent speech with robust cleanup."""
        if self.state == "LISTENING":
            logger.warning(f"⚠️ Session {self.session_id} already listening")
            return True

        # Clean up any stale transcriber before starting fresh
        if self.transcriber:
            logger.info(f"🧹 Cleaning up stale transcriber for session {self.session_id}")
            try:
                # Wait for cleanup to complete with timeout
                await asyncio.wait_for(self.transcriber.stop(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Transcriber cleanup timed out for session {self.session_id}")
            except Exception as e:
                logger.warning(f"⚠️ Error during transcriber cleanup: {e}")

            # Ensure reference is cleared
            self.transcriber = None

            # Add small delay to ensure Deepgram server is ready for new connection
            await asyncio.sleep(0.2)

        # Create fresh transcriber
        self.transcriber = LiveTranscriber(
            on_transcript=self._on_transcript,
            on_speech_final=self._on_speech_final,
            on_error=self._on_error
        )

        # Start with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                success = await self.transcriber.start()
                if success:
                    self.state = "LISTENING"
                    logger.info(f"🎧 Session {self.session_id} started listening (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"⚠️ Transcriber start returned False (attempt {attempt + 1}/{max_retries})")
            except Exception as e:
                logger.error(f"❌ Error starting transcriber (attempt {attempt + 1}/{max_retries}): {e}")

            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = 1.0 * (2 ** attempt)  # 1s, 2s, 4s
                logger.info(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)

        # All retries failed
        logger.error(f"❌ Failed to start transcription after {max_retries} attempts")
        self.transcriber = None
        return False

    def send_audio(self, audio_chunk: bytes):
        """Send audio chunk if in listening state."""
        if self.state != "LISTENING":
            return False

        if self.transcriber:
            return self.transcriber.send_audio(audio_chunk, self.event_loop)
        return False

    async def stop_listening(self):
        """Stop listening (called when AI starts speaking)."""
        if self.transcriber:
            await self.transcriber.stop()
            self.transcriber = None
        self.state = "AI_SPEAKING"
        logger.info(f"🛑 Session {self.session_id} stopped listening")

    def _on_transcript(self, text: str, is_final: bool):
        """Handle transcript updates."""
        if is_final:
            self.final_transcript = text
            self.interim_transcript = ""
        else:
            self.interim_transcript = text

        # Notify server of interim updates (for live display)
        if self.on_interim_update:
            self.on_interim_update(text, is_final)

    def _on_speech_final(self, text: str):
        """Handle speech end detection."""
        if self.state != "LISTENING":
            return

        self.state = "PROCESSING"

        # Text is already accumulated from LiveTranscriber
        logger.info(f"✅ Agent finished speaking: '{text}'")

        # Notify server that agent speech is complete
        if self.on_agent_speech_complete:
            self.on_agent_speech_complete(text)

        # Clear session-level buffers
        self.final_transcript = ""
        self.interim_transcript = ""

    def _on_error(self, error: str):
        """Handle transcription errors."""
        logger.error(f"❌ Transcription error in session {self.session_id}: {error}")
        self.state = "IDLE"


# Test function
async def test_transcriber():
    """Test the live transcriber with console output."""
    print("🎤 Testing Deepgram Live Transcriber...")
    print("   Note: This test connects to Deepgram but needs real audio input to transcribe.")

    def on_transcript(text, is_final):
        status = "FINAL" if is_final else "interim"
        print(f"  [{status}] {text}")

    def on_speech_final(text):
        print(f"  ✅ SPEECH COMPLETE: {text}")

    def on_error(error):
        print(f"  ❌ ERROR: {error}")

    transcriber = LiveTranscriber(
        on_transcript=on_transcript,
        on_speech_final=on_speech_final,
        on_error=on_error
    )

    started = await transcriber.start()
    if started:
        print("✅ Transcriber started successfully")
        print("   Waiting 3 seconds...")
        await asyncio.sleep(3)

        await transcriber.stop()
        print("✅ Test complete")
    else:
        print("❌ Failed to start transcriber")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_transcriber())
