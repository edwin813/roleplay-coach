"""
Web Voice Server - Flask app for voice training platform.
"""
import os
import json
import logging
import traceback
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import base64

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our execution modules
from conversation_manager import TrainingConversation
from score_response import ResponseScorer
from save_training_session import save_session
from synthesize_speech import synthesize_speech
from transcribe_audio import transcribe_audio_stream
from deepgram_streaming import TranscriptionSession
from api_retry import classify_api_error
import auth
import script_store
from manager_routes import manager_bp
from trainee_routes import trainee_bp
import asyncio
import threading

load_dotenv()

# Create dedicated event loop for async Deepgram operations
async_loop = None
async_thread = None

def start_async_loop():
    """Run asyncio event loop in separate thread for Deepgram operations."""
    global async_loop
    async_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(async_loop)
    async_loop.run_forever()

# Start async loop when module loads
async_thread = threading.Thread(target=start_async_loop, daemon=True)
async_thread.start()
print("✅ Async event loop started for Deepgram operations")

app = Flask(__name__,
            template_folder='../web/templates',
            static_folder='../web/static')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active sessions
active_sessions = {}

@app.route('/')
def index():
    """Serve the main training interface."""
    return render_template('index.html')

@app.route('/test')
def test():
    """Serve Socket.IO connection test page."""
    return render_template('test.html')

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "Voice Training Platform"})

@app.route('/api/companies')
def list_companies():
    """List available company scripts in scripts/."""
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
    companies = []
    if os.path.isdir(scripts_dir):
        for filename in sorted(os.listdir(scripts_dir)):
            if not filename.endswith(".json"):
                continue
            try:
                with open(os.path.join(scripts_dir, filename), "r") as f:
                    script = json.load(f)
                companies.append({
                    "id": script.get("id") or filename.replace(".json", ""),
                    "name": script.get("name") or filename.replace(".json", ""),
                    "description": script.get("description", "")
                })
            except Exception as e:
                logger.warning(f"Could not load script {filename}: {e}")
    return jsonify({"companies": companies})

@socketio.on('start_session')
def handle_start_session(data):
    """Initialize a new training session."""
    agent_name = data.get('agent_name', 'Agent')
    difficulty = data.get('difficulty', 'intermediate')
    company_id = data.get('company_id', 'ao_globe_life')
    session_id = data.get('session_id')

    try:
        # Create conversation manager
        conversation = TrainingConversation(agent_name, difficulty, company_id=company_id)
        scorer = ResponseScorer()

        # Create transcription session with the async event loop
        transcription_session = TranscriptionSession(session_id, async_loop)

        # Capture SID before defining async callbacks (request.sid is a
        # thread-local proxy and won't be available from the Deepgram thread)
        sid = request.sid

        # Set up transcription callbacks
        def on_agent_speech_complete(transcript):
            """Called when agent finishes speaking"""
            socketio.emit('agent_speech_detected', {
                'transcript': transcript,
                'session_id': session_id
            }, room=sid)
            # Process the response through conversation manager
            process_agent_transcript(session_id, transcript)

        def on_interim_update(text, is_final):
            """Send interim transcripts to browser"""
            socketio.emit('interim_transcript', {
                'text': text,
                'is_final': is_final
            }, room=sid)

        transcription_session.on_agent_speech_complete = on_agent_speech_complete
        transcription_session.on_interim_update = on_interim_update

        # Store session
        active_sessions[session_id] = {
            'conversation': conversation,
            'scorer': scorer,
            'agent_name': agent_name,
            'difficulty': difficulty,
            'company_id': company_id,
            'start_time': None,
            'responses_evaluated': [],
            'transcription': transcription_session,
            'sid': sid
        }

        # Start session (AI introduction)
        result = conversation.start_session()

        if result['success']:
            # Generate speech for AI message
            speech_result = synthesize_speech(
                text=result['ai_message'],
                output_path=f".tmp/intro_{session_id}.mp3"
            )

            # Read audio file and send as base64
            if speech_result['success']:
                with open(speech_result['audio_path'], 'rb') as f:
                    audio_base64 = base64.b64encode(f.read()).decode('utf-8')

                emit('session_started', {
                    'success': True,
                    'ai_message': result['ai_message'],
                    'audio': audio_base64,
                    'phase': result['phase']
                })
            else:
                emit('session_started', {
                    'success': True,
                    'ai_message': result['ai_message'],
                    'audio': None,
                    'phase': result['phase'],
                    'note': 'Text-only mode (voice synthesis unavailable)'
                })
        else:
            emit('error', {'message': 'Failed to start session'})

    except Exception as e:
        emit('error', {'message': f'Session start error: {str(e)}'})

@socketio.on('start_transcription')
def handle_start_transcription(data):
    """Start Deepgram live transcription for continuous listening."""
    session_id = data.get('session_id')

    if session_id not in active_sessions:
        emit('error', {'message': 'Invalid session'})
        return

    session = active_sessions[session_id]
    transcription = session.get('transcription')

    if not transcription:
        emit('error', {'message': 'Transcription not initialized'})
        return

    # Schedule async start in the dedicated event loop
    future = asyncio.run_coroutine_threadsafe(
        transcription.start_listening(),
        async_loop
    )

    try:
        # Wait for result with generous timeout (allows for cleanup + retries)
        success = future.result(timeout=10.0)
        if success:
            emit('transcription_started', {
                'session_id': session_id,
                'message': 'Ready to receive audio'
            })
        else:
            logger.error(f"❌ Transcription start returned False for session {session_id}")
            emit('error', {
                'message': 'Failed to start transcription. Please wait a moment and try speaking again.',
                'retryable': True
            })
    except asyncio.TimeoutError:
        logger.error(f"❌ Transcription start timed out (>10s) for session {session_id}")
        emit('error', {
            'message': 'Transcription startup timed out. Please wait 5 seconds and try again.',
            'retryable': True
        })
    except Exception as e:
        logger.error(f"❌ Transcription start error for session {session_id}: {type(e).__name__}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        emit('error', {
            'message': f'Transcription error: Unable to restart listening. Please refresh and start a new session.',
            'retryable': False,
            'technical_details': f"{type(e).__name__}: {str(e)}"
        })

audio_chunk_count = {}

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    """Receive audio chunk from browser and send to Deepgram."""
    session_id = data.get('session_id')
    audio_b64 = data.get('audio')  # Base64-encoded audio

    if session_id not in active_sessions:
        return

    session = active_sessions[session_id]
    transcription = session.get('transcription')

    if transcription and transcription.state == "LISTENING" and audio_b64:
        # Decode base64 to raw bytes for Deepgram
        audio_bytes = base64.b64decode(audio_b64)

        # Log first chunk and every 20th chunk to confirm audio is flowing
        audio_chunk_count.setdefault(session_id, 0)
        audio_chunk_count[session_id] += 1
        count = audio_chunk_count[session_id]
        if count == 1 or count % 20 == 0:
            logger.info(f"🎵 Audio chunk #{count} received ({len(audio_bytes)} bytes) for session {session_id}")
        # Send decoded audio bytes to Deepgram
        transcription.send_audio(audio_bytes)

@socketio.on('stop_transcription')
def handle_stop_transcription(data):
    """Stop live transcription (when AI starts speaking)."""
    session_id = data.get('session_id')

    if session_id not in active_sessions:
        return

    session = active_sessions[session_id]
    transcription = session.get('transcription')

    if transcription:
        # Schedule async stop in the dedicated event loop
        future = asyncio.run_coroutine_threadsafe(
            transcription.stop_listening(),
            async_loop
        )

        try:
            future.result(timeout=2.0)
            emit('transcription_stopped', {'session_id': session_id})
        except Exception as e:
            logger.error(f"Error stopping transcription: {e}")

@socketio.on('end_session')
def handle_end_session(data):
    """End the training session when user clicks the mic button."""
    session_id = data.get('session_id')

    if session_id not in active_sessions:
        emit('error', {'message': 'Invalid session'})
        return

    session = active_sessions[session_id]
    transcription = session.get('transcription')

    # Stop transcription if still running
    if transcription and transcription.state == "LISTENING":
        future = asyncio.run_coroutine_threadsafe(
            transcription.stop_listening(),
            async_loop
        )
        try:
            future.result(timeout=2.0)
        except Exception as e:
            logger.error(f"Error stopping transcription during end_session: {e}")

    logger.info(f"🛑 User ended session {session_id} via End Session button")
    handle_session_complete(session_id)

@socketio.on('disconnect')
def handle_disconnect():
    """Clean up any sessions belonging to a disconnected client."""
    sid = request.sid
    orphaned = [sid_session_id for sid_session_id, s in active_sessions.items() if s.get('sid') == sid]
    for session_id in orphaned:
        logger.info(f"🧹 Cleaning up orphaned session {session_id} after disconnect")
        session = active_sessions.get(session_id)
        if not session:
            continue
        transcription = session.get('transcription')
        if transcription and transcription.state == "LISTENING":
            try:
                future = asyncio.run_coroutine_threadsafe(
                    transcription.stop_listening(),
                    async_loop
                )
                future.result(timeout=2.0)
            except Exception as e:
                logger.error(f"Error stopping transcription on disconnect: {e}")
        # Drop the session — no scoring run, client is gone
        active_sessions.pop(session_id, None)

def process_agent_transcript(session_id, transcript):
    """Process transcribed agent response through conversation manager."""
    if session_id not in active_sessions:
        return

    session = active_sessions[session_id]
    conversation = session['conversation']
    scorer = session['scorer']
    transcription = session['transcription']

    # FIX #1: Capture request.sid BEFORE async context to avoid threading issues
    client_sid = request.sid

    async def _score_in_background(session, scorer, result, history, transcript):
        """Score the response without blocking the audio pipeline."""
        try:
            objection_msg = [m for m in history if m.get('objection')][-1]
            score_result = scorer.score_objection_response(
                objection_type=result['objection_type'],
                customer_statement=objection_msg['objection']['statement'],
                agent_response=transcript
            )
            session['responses_evaluated'].append({
                'objection_type': result['objection_type'],
                'score': score_result.get('score', 0),
                'feedback': score_result
            })
            logger.info(f"✅ Background scoring complete: {score_result.get('score', 'N/A')}/10")
        except Exception as e:
            logger.error(f"Background scoring error: {e}")

    async def process_async():
        try:
            # Transcription stop is now triggered by frontend 'stop_transcription' event
            # Just ensure state is correct (fire-and-forget, don't block)
            if transcription.state == "LISTENING":
                asyncio.create_task(transcription.stop_listening())

            # Process response immediately (no waiting on stop)
            result = conversation.process_agent_response(transcript)

            # Get conversation history (needed for filename generation)
            history = conversation.get_conversation_transcript()

            # Generate speech IMMEDIATELY — scoring runs in background AFTER
            logger.info(f"🔊 Generating audio for: {result['ai_message'][:50]}...")
            speech_result = synthesize_speech(
                text=result['ai_message'],
                output_path=f".tmp/response_{session_id}_{len(history)}.mp3"
            )

            logger.info(f"🔊 Speech synthesis result: {speech_result.get('success', False)}")
            if not speech_result['success']:
                logger.error(f"❌ Audio generation error: {speech_result.get('error', 'Unknown error')}")

            if speech_result['success']:
                with open(speech_result['audio_path'], 'rb') as f:
                    audio_base64 = base64.b64encode(f.read()).decode('utf-8')
                logger.info(f"✅ Audio generated, size: {len(audio_base64)} bytes")
            else:
                audio_base64 = None
                logger.warning("⚠️ No audio generated, sending text only")

            # Send response back FIRST (user hears audio ASAP)
            socketio.emit('ai_response', {
                'success': True,
                'ai_message': result['ai_message'],
                'audio': audio_base64,
                'phase': result['phase'],
                'session_complete': result.get('session_complete', False)
            }, room=client_sid)

            # AFTER audio is sent, score in background (non-blocking)
            if result.get('objection_type'):
                asyncio.create_task(_score_in_background(
                    session, scorer, result, history, transcript
                ))

            # If session complete, calculate final score
            if result.get('session_complete'):
                handle_session_complete(session_id)
            else:
                # Restart transcription for next agent response
                await transcription.start_listening()

        except Exception as e:
            socketio.emit('error', {
                'message': f'Processing error: {str(e)}'
            }, room=client_sid)

    # FIX #2: Schedule async processing and capture future for error handling
    future = asyncio.run_coroutine_threadsafe(process_async(), async_loop)

    # Add error callback to log failures
    def on_done(fut):
        try:
            fut.result()  # This will re-raise any exception
        except Exception as e:
            logger.error(f"❌ Error in process_async for session {session_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    future.add_done_callback(on_done)

@socketio.on('agent_response')
def handle_agent_response(data):
    """Process agent's spoken response."""
    session_id = data.get('session_id')
    audio_data = data.get('audio')  # Base64 encoded audio
    text = data.get('text')  # Or pre-transcribed text

    if session_id not in active_sessions:
        emit('error', {'message': 'Invalid session'})
        return

    session = active_sessions[session_id]
    conversation = session['conversation']
    scorer = session['scorer']

    try:
        # Transcribe if audio provided
        if audio_data and not text:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_data)

            # Transcribe
            transcription = transcribe_audio_stream(audio_bytes)
            if not transcription['success']:
                emit('error', {'message': 'Transcription failed'})
                return

            text = transcription['transcript']
            confidence = transcription.get('confidence', 0)

            # Check transcription quality
            if confidence < 0.6:
                emit('clarification_needed', {
                    'message': 'Sorry, I did not catch that clearly. Could you repeat?'
                })
                return

        # Process response through conversation manager
        result = conversation.process_agent_response(text)

        # FIX: Always get conversation history (needed for filename generation)
        history = conversation.get_conversation_transcript()

        # If objection was presented, score the response
        if result.get('objection_type'):
            # Get the previous customer message (the objection)
            objection_msg = [m for m in history if m.get('objection')][-1]

            # Score the agent's response
            score_result = scorer.score_objection_response(
                objection_type=result['objection_type'],
                customer_statement=objection_msg['objection']['statement'],
                agent_response=text
            )

            session['responses_evaluated'].append({
                'objection_type': result['objection_type'],
                'score': score_result.get('score', 0),
                'feedback': score_result
            })

        # Generate speech for AI response
        speech_result = synthesize_speech(
            text=result['ai_message'],
            output_path=f".tmp/response_{session_id}_{len(history)}.mp3"
        )

        if speech_result['success']:
            with open(speech_result['audio_path'], 'rb') as f:
                audio_base64 = base64.b64encode(f.read()).decode('utf-8')
        else:
            audio_base64 = None

        # Send response back
        emit('ai_response', {
            'success': True,
            'ai_message': result['ai_message'],
            'audio': audio_base64,
            'phase': result['phase'],
            'session_complete': result.get('session_complete', False)
        })

        # If session complete, calculate final score
        if result.get('session_complete'):
            handle_session_complete(session_id)

    except Exception as e:
        emit('error', {'message': f'Processing error: {str(e)}'})

def handle_session_complete(session_id):
    """Calculate final score and save session with robust error handling."""
    if session_id not in active_sessions:
        return

    session = active_sessions[session_id]
    conversation = session['conversation']
    scorer = session['scorer']

    try:
        # Get full conversation
        history = conversation.get_conversation_transcript()
        objections_presented = conversation.objections_presented

        # Calculate comprehensive score with retry and fallback
        try:
            final_scores = scorer.score_full_session(history, objections_presented)
        except Exception as scoring_error:
            error_info = classify_api_error(scoring_error)

            logger.error(f"❌ Scoring failed: {error_info['technical_message']}")

            # Emit user-friendly error notification
            socketio.emit('scoring_error', {
                'message': error_info['user_message'],
                'retryable': error_info['retryable'],
                'session_id': session_id
            }, room=request.sid)

            # Use fallback scoring if API fails
            final_scores = {
                'final_score': 7.0,  # Neutral score
                'grade': 'B',
                'objections_handled': len(objections_presented),
                'category_scores': {
                    'objection_handling': 7,
                    'tone_confidence': 7,
                    'script_adherence': 7,
                    'active_listening': 7,
                    'professionalism': 7
                },
                'needs_trainer_followup': True,  # Flag for manual review
                'scoring_error': error_info['user_message']
            }

        # Prepare session data for saving
        session_data = {
            'agent_name': session['agent_name'],
            'difficulty': session['difficulty'],
            'duration_minutes': 10,  # Would calculate from start_time
            'final_score': final_scores['final_score'],
            'grade': final_scores['grade'],
            'objections_handled': final_scores['objections_handled'],
            'objection_handling_score': final_scores['category_scores']['objection_handling'],
            'tone_score': final_scores['category_scores']['tone_confidence'],
            'script_adherence_score': final_scores['category_scores']['script_adherence'],
            'active_listening_score': final_scores['category_scores']['active_listening'],
            'professionalism_score': final_scores['category_scores']['professionalism'],
            'improvements': [],  # Would extract from scoring feedback
            'transcript_link': '',  # Would upload transcript somewhere
            'needs_trainer_followup': final_scores.get('needs_trainer_followup', False),
            'scoring_error': final_scores.get('scoring_error', None)
        }

        # Save to Google Sheets (best effort, non-blocking)
        try:
            save_result = save_session(session_data)
        except Exception as save_error:
            logger.error(f"❌ Failed to save session: {str(save_error)}")
            save_result = {'success': False, 'error': str(save_error)}

        # Send final results to client (always, even if scoring failed)
        socketio.emit('session_complete', {
            'scores': final_scores,
            'transcript': history,
            'saved': save_result.get('success', False),
            'warnings': final_scores.get('scoring_error', None)
        }, room=request.sid)

        # Clean up session
        del active_sessions[session_id]

    except Exception as e:
        logger.error(f"❌ Critical error in session completion: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        error_info = classify_api_error(e)

        socketio.emit('error', {
            'message': f'Session completion error: {error_info["user_message"]}',
            'retryable': error_info['retryable'],
            'technical_details': error_info['technical_message']
        }, room=request.sid)

@app.route('/api/test')
def test_api():
    """Test endpoint to verify server is running."""
    return jsonify({
        "status": "ok",
        "message": "Voice Training API is running",
        "endpoints": {
            "main": "/",
            "health": "/health",
            "websocket": "Connect via Socket.IO"
        }
    })

if __name__ == '__main__':
    print("🎙️  Starting Voice Training Platform...")
    print("📍 Server running at: http://localhost:5001")
    print("🔌 WebSocket ready for connections")
    print("\nPress Ctrl+C to stop\n")

    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
