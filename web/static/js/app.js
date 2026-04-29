// Voice Training Platform - Frontend Application with Deepgram Live Streaming

class VoiceTrainingApp {
    constructor() {
        this.socket = null;
        this.sessionId = null;
        this.mediaRecorder = null;
        this.audioStream = null;
        this.currentAudio = null;
        this.isSocketConnected = false;  // Track Socket.IO connection status

        // State machine
        this.state = "IDLE";  // IDLE, AI_SPEAKING, LISTENING, PROCESSING

        // Transcription retry tracking
        this.transcriptionRetryCount = 0;
        this.maxTranscriptionRetries = 2;

        // Audio configuration
        this.audioContext = null;
        this.audioChunks = [];

        this.init();
    }

    init() {
        // Connect Socket.IO
        console.log('🔌 Initializing Socket.IO connection...');
        console.log('🔌 Connecting to:', window.location.origin);

        this.socket = io({
            transports: ['polling', 'websocket'],
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            timeout: 10000
        });

        // Set up event listeners
        this.setupSocketListeners();
        this.setupUIListeners();
        this.loadCompanies();

        // Log socket state and enable fallback
        setTimeout(() => {
            console.log('Socket.IO state after 5s:', {
                connected: this.socket.connected,
                id: this.socket.id,
                disconnected: this.socket.disconnected,
                isSocketConnected: this.isSocketConnected
            });

            // Fallback: If not connected after 5 seconds, check manually
            if (!this.isSocketConnected && this.socket.connected) {
                console.log('⚠️ Connected but flag not set, fixing...');
                this.isSocketConnected = true;
                this.enableStartButton();
            } else if (!this.isSocketConnected) {
                console.error('❌ Still not connected after 5 seconds');
                console.error('Socket object:', this.socket);
            }
        }, 5000);
    }

    setupSocketListeners() {
        this.socket.on('connect', () => {
            console.log('✅ Connected to server with ID:', this.socket.id);
            this.isSocketConnected = true;
            this.updateStatus('connected');
            this.enableStartButton();
        });

        this.socket.on('disconnect', (reason) => {
            console.log('⚠️ Disconnected from server. Reason:', reason);
            this.isSocketConnected = false;
            this.updateStatus('disconnected');
            this.disableStartButton();
        });

        this.socket.on('connect_error', (error) => {
            console.error('❌ Socket.IO connection error:', error);
            console.error('Error message:', error.message);
            console.error('Error description:', error.description);
            const statusText = document.getElementById('connection-status-text');
            if (statusText) {
                statusText.textContent = 'Connection error: ' + error.message;
                statusText.style.color = '#f44336';
            }
            this.disableStartButton();
        });

        this.socket.on('connect_timeout', () => {
            console.error('❌ Socket.IO connection timeout');
            const statusText = document.getElementById('connection-status-text');
            if (statusText) {
                statusText.textContent = 'Connection timeout';
                statusText.style.color = '#f44336';
            }
            this.disableStartButton();
        });

        this.socket.on('error', (error) => {
            console.error('❌ Socket.IO error:', error);
        });

        this.socket.on('session_started', (data) => {
            console.log('Session started', data);
            this.handleSessionStarted(data);
        });

        this.socket.on('transcription_started', (data) => {
            console.log('✅ Transcription started successfully');
            this.transcriptionRetryCount = 0;  // Reset retry counter on success
            this.startAudioStreaming();
        });

        this.socket.on('interim_transcript', (data) => {
            // Display interim transcript as user speaks
            document.getElementById('live-transcript').textContent = data.text;
            if (data.is_final) {
                document.getElementById('live-transcript').style.fontWeight = 'bold';
            } else {
                document.getElementById('live-transcript').style.fontWeight = 'normal';
            }
        });

        this.socket.on('agent_speech_detected', (data) => {
            console.log('Agent speech complete:', data.transcript);
            this.addMessage('agent', data.transcript);
            document.getElementById('live-transcript').textContent = '';
            this.state = "PROCESSING";

            // IMMEDIATELY stop recording and update UI
            this.stopAudioStreaming();
            document.querySelector('.mic-text').textContent = 'AI is thinking...';

            // Tell server to stop transcription (frontend-initiated)
            this.socket.emit('stop_transcription', {
                session_id: this.sessionId
            });
        });

        this.socket.on('ai_response', (data) => {
            console.log('AI response received', data);
            this.handleAIResponse(data);
        });

        this.socket.on('session_complete', (data) => {
            console.log('Session complete', data);
            this.handleSessionComplete(data);
        });

        this.socket.on('error', (data) => {
            console.error('Error:', data);

            // Check if this is a transcription error
            if (data.message && data.message.includes('Transcription')) {
                const handled = this.handleTranscriptionError(data);
                if (handled) return;  // Auto-retry in progress
            }

            // Not transcription error or couldn't handle - show to user
            let errorMessage = data.message || 'An error occurred';

            // Add retry guidance for retryable errors
            if (data.retryable) {
                errorMessage += '\n\nThis is a temporary issue. Please wait 30 seconds and try again.';
            }

            alert(`Error: ${errorMessage}`);
        });

        this.socket.on('scoring_error', (data) => {
            console.warn('Scoring error:', data);

            // Show user-friendly warning (not an error, session continues)
            const warningDiv = document.createElement('div');
            warningDiv.className = 'warning-message';
            warningDiv.style.cssText = `
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                color: #856404;
                padding: 15px;
                margin: 10px 0;
                border-radius: 4px;
                font-size: 14px;
            `;
            warningDiv.innerHTML = `
                <strong>⚠️ Scoring Delayed</strong><br>
                ${data.message}<br>
                <small style="display: block; margin-top: 8px;">
                    Your session is being completed with estimated scores.
                    A trainer will review your performance.
                </small>
            `;

            const messagesDiv = document.querySelector('.messages') || document.body;
            messagesDiv.appendChild(warningDiv);

            // Auto-dismiss after 10 seconds
            setTimeout(() => warningDiv.remove(), 10000);
        });

        this.socket.on('transcription_stopped', (data) => {
            console.log('Transcription stopped');
            this.stopAudioStreaming();
        });
    }

    setupUIListeners() {
        // Setup form
        document.getElementById('setup-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startSession();
        });

        // Disable button initially until socket connects
        this.disableStartButton();

        // Start new session
        document.getElementById('start-new').addEventListener('click', () => {
            this.resetApp();
        });

        // FIX: View transcript button
        document.getElementById('view-transcript').addEventListener('click', () => {
            this.showTranscript();
        });

        // Mic button: secondary path to end the call (only meaningful while listening)
        document.getElementById('mic-button').addEventListener('click', () => {
            if (this.state === "LISTENING") {
                this.endSession();
            }
        });

        // End Session button: always-on hang up. Confirms the user really wants to end.
        document.getElementById('end-session-button').addEventListener('click', () => {
            if (this.endSessionInProgress) return;
            this.endSession();
        });
    }

    async loadCompanies() {
        const select = document.getElementById('company-select');
        if (!select) return;
        try {
            const res = await fetch('/api/companies');
            const data = await res.json();
            const companies = data.companies || [];
            if (companies.length === 0) {
                select.innerHTML = '<option value="">No scripts found</option>';
                return;
            }
            select.innerHTML = companies.map(c =>
                `<option value="${c.id}">${c.name}</option>`
            ).join('');
        } catch (err) {
            console.error('Failed to load companies:', err);
            select.innerHTML = '<option value="ao_globe_life">AO / Globe Life (default)</option>';
        }
    }

    enableStartButton() {
        const button = document.querySelector('#setup-form button[type="submit"]');
        const statusText = document.getElementById('connection-status-text');

        if (button) {
            button.disabled = false;
            button.textContent = 'Start Training';
            button.style.opacity = '1';
        }

        if (statusText) {
            statusText.textContent = 'Connected';
            statusText.style.color = '#4caf50';
        }
    }

    disableStartButton() {
        const button = document.querySelector('#setup-form button[type="submit"]');
        const statusText = document.getElementById('connection-status-text');

        if (button) {
            button.disabled = true;
            button.textContent = 'Connecting...';
            button.style.opacity = '0.6';
        }

        if (statusText) {
            statusText.textContent = 'Connecting...';
            statusText.style.color = '#ff9800';
        }
    }

    async requestMicrophoneAccess() {
        // Request microphone permission and initialize audio stream
        try {
            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,  // 16kHz for Deepgram
                    channelCount: 1,  // Mono
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            console.log('✅ Microphone access granted');
            return true;
        } catch (error) {
            console.error('❌ Microphone access denied:', error);
            alert('Please allow microphone access to use voice training');
            return false;
        }
    }

    startSession() {
        // Validate socket is connected before starting session
        if (!this.isSocketConnected) {
            console.error('❌ Socket not connected, cannot start session');
            alert('Connection not ready. Please wait and try again.');
            return;
        }

        const agentName = document.getElementById('agent-name').value;
        const difficulty = document.getElementById('difficulty').value;
        const companySelect = document.getElementById('company-select');
        const companyId = companySelect && companySelect.value ? companySelect.value : 'ao_globe_life';

        this.sessionId = this.generateSessionId();
        this.endSessionInProgress = false;

        document.getElementById('current-agent').textContent = agentName;

        console.log('🚀 Starting session with socket connected:', this.isSocketConnected, 'company:', companyId);

        this.socket.emit('start_session', {
            agent_name: agentName,
            difficulty: difficulty,
            company_id: companyId,
            session_id: this.sessionId
        });

        this.showScreen('training-screen');

        // End Session button is live as soon as the session screen opens
        const endBtn = document.getElementById('end-session-button');
        if (endBtn) endBtn.disabled = false;
    }

    async handleSessionStarted(data) {
        if (!data.success) return;

        this.addMessage('ai', data.ai_message);
        document.getElementById('current-phase').textContent = data.phase;

        // Request microphone access
        const micGranted = await this.requestMicrophoneAccess();
        if (!micGranted) {
            alert('Cannot proceed without microphone access');
            return;
        }

        // Play AI audio
        if (data.audio) {
            await this.playAudio(data.audio);
        }

        // After AI finishes, automatically start transcription
        setTimeout(() => {
            this.startTranscription();
        }, 800);  // Natural pause
    }

    async handleAIResponse(data) {
        if (!data.success) return;

        this.addMessage('ai', data.ai_message);
        document.getElementById('current-phase').textContent = data.phase;

        // Play audio
        if (data.audio) {
            await this.playAudio(data.audio);
        }

        // Check if session complete
        if (data.session_complete) {
            // Will receive session_complete event next
            this.state = "IDLE";
            this.stopAudioStreaming();
        } else {
            // Continue conversation - restart transcription after AI speaks
            setTimeout(() => {
                this.startTranscription();
            }, 800);
        }
    }

    handleSessionComplete(data) {
        const scores = data.scores;

        // FIX: Store transcript data for viewing
        this.sessionTranscript = data.transcript || [];

        // Display final score
        document.getElementById('final-score').textContent = `${scores.final_score}/10`;
        document.getElementById('grade-badge').textContent = scores.grade;

        // Display category scores
        const categoryScores = scores.category_scores;
        const container = document.getElementById('category-scores');
        container.innerHTML = '';

        for (const [category, score] of Object.entries(categoryScores)) {
            const item = document.createElement('div');
            item.className = 'score-item';

            const label = document.createElement('span');
            label.textContent = this.formatCategoryName(category);

            const bar = document.createElement('div');
            bar.className = 'score-bar';

            const fill = document.createElement('div');
            fill.className = 'score-fill';
            fill.style.width = `${score * 10}%`;
            fill.textContent = `${score}/10`;

            bar.appendChild(fill);
            item.appendChild(label);
            item.appendChild(bar);

            container.appendChild(item);
        }

        // Display feedback
        const feedbackContent = document.getElementById('feedback-content');
        feedbackContent.innerHTML = this.generateFeedback(scores);

        this.showScreen('results-screen');
    }

    handleTranscriptionError(errorData) {
        console.error('Transcription error:', errorData);

        // If retryable and we haven't exceeded retries, try again
        if (errorData.retryable && this.transcriptionRetryCount < this.maxTranscriptionRetries) {
            this.transcriptionRetryCount++;
            const retryDelay = 2000 * this.transcriptionRetryCount;  // 2s, 4s

            console.log(`⏳ Auto-retrying transcription in ${retryDelay}ms (attempt ${this.transcriptionRetryCount}/${this.maxTranscriptionRetries})`);

            // Show temporary message
            this.showWarning(`Reconnecting... (attempt ${this.transcriptionRetryCount}/${this.maxTranscriptionRetries})`);

            setTimeout(() => {
                this.startTranscription();
            }, retryDelay);

            return true;  // Handled with retry
        }

        // Can't retry or retries exhausted - show error to user
        this.transcriptionRetryCount = 0;  // Reset for next time
        return false;  // Not handled
    }

    showWarning(message) {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'warning-message';
        warningDiv.style.background = '#fff3cd';
        warningDiv.style.color = '#856404';
        warningDiv.style.padding = '12px';
        warningDiv.style.marginBottom = '10px';
        warningDiv.style.borderRadius = '4px';
        warningDiv.textContent = message;

        const messagesDiv = document.querySelector('.messages');
        messagesDiv.appendChild(warningDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => warningDiv.remove(), 5000);
    }

    showTranscript() {
        // Guard: Check if transcript exists
        if (!this.sessionTranscript || this.sessionTranscript.length === 0) {
            alert('No transcript available');
            return;
        }

        // Create modal overlay
        const modal = document.createElement('div');
        modal.className = 'transcript-modal';
        modal.innerHTML = `
            <div class="transcript-modal-content">
                <div class="transcript-header">
                    <h2>📝 Training Session Transcript</h2>
                    <button class="close-transcript">×</button>
                </div>
                <div class="transcript-body">
                    ${this.formatTranscript(this.sessionTranscript)}
                </div>
                <div class="transcript-footer">
                    <button class="btn btn-secondary close-transcript">Close</button>
                </div>
            </div>
        `;

        // Append to body
        document.body.appendChild(modal);

        // Close button handlers
        modal.querySelectorAll('.close-transcript').forEach(btn => {
            btn.addEventListener('click', () => {
                modal.remove();
            });
        });

        // Click outside to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    formatTranscript(transcript) {
        // Format transcript messages into readable HTML
        return transcript.map(msg => {
            const roleLabel = msg.role === 'ai' ? '🤖 Customer' : '👤 You';
            const roleClass = msg.role === 'ai' ? 'transcript-ai' : 'transcript-agent';

            return `
                <div class="transcript-message ${roleClass}">
                    <div class="transcript-role">${roleLabel}</div>
                    <div class="transcript-content">${msg.content}</div>
                    <div class="transcript-phase">${msg.phase}</div>
                </div>
            `;
        }).join('');
    }

    startTranscription() {
        // Start Deepgram live transcription
        console.log('🎙️ Starting transcription...');
        this.state = "LISTENING";

        // Update UI — enable mic button so its end-call shortcut actually fires
        const micBtn = document.getElementById('mic-button');
        document.querySelector('.mic-text').textContent = 'Listening...';
        micBtn.classList.add('recording');
        micBtn.disabled = false;

        // Tell server to start transcription
        this.socket.emit('start_transcription', {
            session_id: this.sessionId
        });
    }

    async startAudioStreaming() {
        // Start capturing and streaming audio chunks to server
        if (!this.audioStream) {
            console.error('❌ No audio stream available');
            return;
        }

        try {
            // Create MediaRecorder to capture audio
            let mimeType = 'audio/webm;codecs=opus';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'audio/webm';
            }

            this.mediaRecorder = new MediaRecorder(this.audioStream, {
                mimeType: mimeType,
                audioBitsPerSecond: 128000
            });

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && this.state === "LISTENING") {
                    // Convert Blob to base64 for reliable Socket.IO transport
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const base64 = reader.result.split(',')[1];
                        this.socket.emit('audio_chunk', {
                            session_id: this.sessionId,
                            audio: base64
                        });
                    };
                    reader.readAsDataURL(event.data);
                }
            };

            this.mediaRecorder.onerror = (event) => {
                console.error('❌ MediaRecorder error:', event.error);
            };

            // Start recording, send chunks every 250ms
            this.mediaRecorder.start(250);
            console.log('✅ Audio streaming started');

        } catch (error) {
            console.error('❌ Error starting audio streaming:', error);
        }
    }

    stopAudioStreaming() {
        // Stop capturing audio
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
            console.log('🛑 Audio streaming stopped');
        }

        // Update UI — mic is no longer the live "end call" target
        const micBtn = document.getElementById('mic-button');
        micBtn.classList.remove('recording');
        micBtn.disabled = true;
        document.querySelector('.mic-text').textContent = 'AI is thinking...';
    }

    endSession() {
        // End the call (End Session button or mic button while listening)
        if (this.endSessionInProgress) return;
        this.endSessionInProgress = true;

        console.log('🛑 User ended session');
        this.stopAudioStreaming();
        this.state = "PROCESSING";
        document.querySelector('.mic-text').textContent = 'Ending session...';

        // Lock both controls so the user can't double-fire end_session
        const micBtn = document.getElementById('mic-button');
        const endBtn = document.getElementById('end-session-button');
        if (micBtn) micBtn.disabled = true;
        if (endBtn) {
            endBtn.disabled = true;
            const endText = endBtn.querySelector('.end-text');
            if (endText) endText.textContent = 'Ending…';
        }

        // Tell server to stop transcription and wrap up
        this.socket.emit('stop_transcription', {
            session_id: this.sessionId
        });
        this.socket.emit('end_session', {
            session_id: this.sessionId
        });
    }

    async playAudio(base64Audio) {
        // Play AI response audio
        this.state = "AI_SPEAKING";
        this.stopAudioStreaming();

        // Update UI
        document.querySelector('.mic-text').textContent = 'AI is speaking...';

        // Debug: log received audio
        console.log('📥 Audio data received:', base64Audio ? base64Audio.substring(0, 50) + '...' : 'null');

        if (!base64Audio) {
            console.error('❌ No audio data received');
            this.state = "IDLE";
            return;
        }

        // Try multiple MIME types for compatibility
        const mimeTypes = ['audio/mpeg', 'audio/mp3', 'audio/wav'];
        let audio = null;

        for (const mimeType of mimeTypes) {
            audio = new Audio(`data:${mimeType};base64,${base64Audio}`);

            // Test if browser can play this type
            const canPlay = audio.canPlayType(mimeType);
            console.log(`Can play ${mimeType}:`, canPlay);

            if (canPlay !== '') {
                console.log(`✅ Using MIME type: ${mimeType}`);
                break;  // Use this MIME type
            }
        }

        return new Promise((resolve) => {
            audio.onended = () => {
                console.log('✅ AI finished speaking');
                this.state = "IDLE";
                resolve();
            };

            audio.onerror = (error) => {
                console.error('❌ Audio playback error:', error);
                console.error('Audio source (first 100 chars):', audio.src.substring(0, 100));
                this.state = "IDLE";
                resolve();
            };

            audio.play().then(() => {
                console.log('▶️ Audio playing...');
            }).catch(error => {
                console.error('❌ Error starting playback:', error);
                this.state = "IDLE";
                resolve();
            });

            this.currentAudio = audio;
        });
    }

    addMessage(role, content) {
        const conversation = document.getElementById('conversation');

        const message = document.createElement('div');
        message.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'ai' ? '🤖' : '👤';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = content;

        message.appendChild(avatar);
        message.appendChild(messageContent);

        conversation.appendChild(message);

        // Scroll to bottom
        conversation.parentElement.scrollTop = conversation.parentElement.scrollHeight;
    }

    updateStatus(status) {
        const statusDot = document.getElementById('connection-status');
        statusDot.style.background = status === 'connected' ? '#4caf50' : '#f44336';
    }

    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        document.getElementById(screenId).classList.add('active');
    }

    resetApp() {
        this.sessionId = null;
        this.state = "IDLE";
        this.endSessionInProgress = false;

        // Stop any active audio streaming
        this.stopAudioStreaming();

        // Release microphone
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
            this.audioStream = null;
        }

        // Reset End Session button label/state
        const endBtn = document.getElementById('end-session-button');
        if (endBtn) {
            endBtn.disabled = true;
            const endText = endBtn.querySelector('.end-text');
            if (endText) endText.textContent = 'End Session';
        }

        document.getElementById('conversation').innerHTML = '';
        document.getElementById('live-transcript').textContent = '';
        this.showScreen('setup-screen');
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    formatCategoryName(name) {
        return name
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    generateFeedback(scores) {
        const score = scores.final_score;
        let feedback = '';

        if (score >= 9.0) {
            feedback = `<p><strong>🌟 Outstanding performance!</strong></p>
                        <p>You demonstrated excellent objection handling, professional tone, and strong rapport-building skills. You're ready for live calls!</p>`;
        } else if (score >= 7.0) {
            feedback = `<p><strong>✅ Great job!</strong></p>
                        <p>You handled most objections well and maintained professionalism. Review the specific feedback above to reach the next level.</p>`;
        } else if (score >= 5.0) {
            feedback = `<p><strong>⚠️ Making progress</strong></p>
                        <p>You're developing your skills, but there are key areas that need improvement. Focus on the lowest-scoring categories and practice those specific objections.</p>`;
        } else {
            feedback = `<p><strong>📚 Keep practicing</strong></p>
                        <p>This session showed areas that need significant work. Your trainer will be notified for one-on-one coaching. Don't get discouraged - everyone improves with practice!</p>`;
        }

        return feedback;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new VoiceTrainingApp();
});
