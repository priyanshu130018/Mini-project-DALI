class DALIClient {
    constructor() {
        this.ws = null;
        this.wsUrl = 'ws://localhost:8765/ws';
        this.voiceMode = false;
        this.isConnected = false;
        this.ttsEnabled = true;
        this.recognition = null;
        this.isListening = false;

        this.initElements();
        this.initVoiceRecognition();
        this.initEventListeners();
        this.connect();
    }

    initElements() {
        this.statusDot = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        this.chatContainer = document.getElementById('chatContainer');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.micBtn = document.getElementById('micBtn');
        this.speakerBtn = document.getElementById('speakerBtn');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.languageInfo = document.getElementById('languageInfo');
        this.voiceToggleBtn = document.getElementById('voiceToggleBtn'); // optional manual toggle
    }

    initEventListeners() {
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.micBtn.addEventListener('click', () => this.toggleListening());
        this.speakerBtn.addEventListener('click', () => this.toggleTTS());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        if (this.voiceToggleBtn) {
            this.voiceToggleBtn.addEventListener('click', () => {
                this.voiceMode = !this.voiceMode;
                if (this.voiceMode) {
                    this.startListening();
                    this.showListeningAnimation();
                } else {
                    this.stopListening();
                    this.hideListeningAnimation();
                }
            });
        }
    }

    connect() {
        this.ws = new WebSocket(this.wsUrl);
        this.ws.onopen = () => this.onConnect();
        this.ws.onmessage = (event) => this.onMessage(event);
        this.ws.onerror = (error) => this.onError(error);
        this.ws.onclose = () => this.onDisconnect();
    }

    onConnect() {
        this.isConnected = true;
        this.updateStatus(true, 'Connected');
        this.messageInput.disabled = false;
        this.sendBtn.disabled = false;
        this.micBtn.disabled = false;
        this.speakerBtn.disabled = false;
        this.addSystemMessage('✅ Connected to DALI Assistant');
    }

    onMessage(event) {
        const msg = JSON.parse(event.data);
        if (msg.event === 'voice_mode') {
            this.voiceMode = msg.enabled;
            if (this.voiceMode) {
                this.startListening();
                this.showListeningAnimation();
            } else {
                this.stopListening();
                this.hideListeningAnimation();
            }
        }
        if (msg.text) {
            this.hideTypingIndicator();
            this.addBotMessage(msg.text);
            if (msg.speak && this.ttsEnabled) {
                this.speak(msg.text);
            }
            if (msg.language) {
                this.updateLanguage(msg.language);
            }
        }
        if (msg.type === 'system') {
            this.addSystemMessage(msg.message);
        }
        if (msg.type === 'error') {
            this.addSystemMessage(`❌ ${msg.message}`);
        }
    }

    initVoiceRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            this.addSystemMessage('❌ Voice input not supported in this browser');
            return;
        }
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            this.isListening = true;
            this.micBtn.classList.add('listening');
            this.micBtn.textContent = '🔴';
            this.addSystemMessage('🎤 Listening...');
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.messageInput.value = transcript;
            this.sendMessage();
        };

        this.recognition.onerror = (event) => {
            this.addSystemMessage(`❌ Voice error: ${event.error}`);
            this.stopListening();
        };

        this.recognition.onend = () => {
            this.stopListening();
        };
    }

    toggleListening() {
        if (!this.recognition) {
            this.addSystemMessage('❌ Voice input not supported in this browser');
            return;
        }
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }

    startListening() {
        try {
            if (this.recognition && !this.isListening) {
                this.recognition.start();
            }
        } catch (e) {
            console.error('Start listening error:', e);
        }
    }

    stopListening() {
        this.isListening = false;
        this.micBtn.classList.remove('listening');
        this.micBtn.textContent = '🎤';
        if (this.recognition) {
            this.recognition.stop();
        }
    }

    showListeningAnimation() {
        this.micBtn.classList.add('active');
    }

    hideListeningAnimation() {
        this.micBtn.classList.remove('active');
    }

    toggleTTS() {
        this.ttsEnabled = !this.ttsEnabled;
        this.speakerBtn.textContent = this.ttsEnabled ? '🔊' : '🔇';
        this.speakerBtn.classList.toggle('muted', !this.ttsEnabled);
        this.addSystemMessage(this.ttsEnabled ? '🔊 Voice output enabled' : '🔇 Voice output disabled');
        if (this.isConnected) {
            this.ws.send(JSON.stringify({ type: 'toggle_tts', enabled: this.ttsEnabled }));
        }
    }

    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || !this.isConnected) return;
        this.addUserMessage(message);
        this.messageInput.value = '';
        this.showTypingIndicator();
        this.ws.send(JSON.stringify({ type: 'text', message }));
    }

    addUserMessage(text) {
        const div = document.createElement('div');
        div.className = 'message user';
        div.innerHTML = `<div><div class="message-content">${this.escapeHtml(text)}</div><div class="message-time">${this.getCurrentTime()}</div></div>`;
        this.chatContainer.appendChild(div);
        this.scrollToBottom();
    }

    addBotMessage(text) {
        const div = document.createElement('div');
        div.className = 'message bot';
        div.innerHTML = `<div><div class="message-content">${this.escapeHtml(text)}</div><div class="message-time">${this.getCurrentTime()}</div></div>`;
        this.chatContainer.appendChild(div);
        this.scrollToBottom();
    }

    addSystemMessage(text) {
        const div = document.createElement('div');
        div.className = 'system-message';
        div.textContent = text;
        this.chatContainer.appendChild(div);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        this.typingIndicator.classList.remove('hidden');
    }

    hideTypingIndicator() {
        this.typingIndicator.classList.add('hidden');
    }

    updateStatus(connected, text) {
        this.statusDot.className = connected ? 'status-dot connected' : 'status-dot disconnected';
        this.statusText.textContent = text;
    }

    updateLanguage(language) {
        const flag = language === 'hindi' ? '🇮🇳' : '🇬🇧';
        this.languageInfo.textContent = `${flag} ${language}`;
    }

    scrollToBottom() {
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }

    getCurrentTime() {
        return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    onError(error) {
        console.error('WebSocket error:', error);
    }

    onDisconnect() {
        this.isConnected = false;
        this.updateStatus(false, 'Disconnected');
        this.messageInput.disabled = true;
        this.sendBtn.disabled = true;
        this.micBtn.disabled = true;
        this.speakerBtn.disabled = true;
        this.stopListening();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.daliClient = new DALIClient();
    console.log('✅ DALI Client with Voice Input Initialized');
});
