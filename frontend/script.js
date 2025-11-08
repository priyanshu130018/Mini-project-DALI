// ========================================
// DALI Client with Voice Input
// ========================================

class DALIClient {
    constructor() {
        this.ws = null;
        this.wsUrl = 'ws://localhost:8765';
        this.isConnected = false;
        this.ttsEnabled = true;
        this.synth = window.speechSynthesis;
        
        // Voice Recognition
        this.recognition = null;
        this.isListening = false;
        this.initVoiceRecognition();
        
        this.initElements();
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
    }

    initVoiceRecognition() {
        // Check if browser supports Web Speech API
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
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
                console.error('Speech recognition error:', event.error);
                this.addSystemMessage(`❌ Voice error: ${event.error}`);
                this.stopListening();
            };

            this.recognition.onend = () => {
                this.stopListening();
            };
        } else {
            console.warn('Speech recognition not supported');
        }
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
            this.recognition.start();
        } catch (error) {
            console.error('Start listening error:', error);
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

    connect() {
        try {
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = () => this.onConnect();
            this.ws.onmessage = (event) => this.onMessage(event);
            this.ws.onerror = (error) => this.onError(error);
            this.ws.onclose = () => this.onDisconnect();
            
        } catch (error) {
            console.error('WebSocket error:', error);
            this.updateStatus(false, 'Connection Failed');
        }
    }

    onConnect() {
        this.isConnected = true;
        this.updateStatus(true, 'Connected');
        this.messageInput.disabled = false;
        this.sendBtn.disabled = false;
        this.micBtn.disabled = false;
        this.speakerBtn.disabled = false;
        
        const welcomeMsg = document.querySelector('.welcome-message');
        if (welcomeMsg) welcomeMsg.remove();
        
        this.addSystemMessage('✅ Connected to DALI Assistant');
    }

    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('Received:', data);

            switch(data.type) {
                case 'system':
                    this.addSystemMessage(data.message);
                    break;
                
                case 'response':
                    this.hideTypingIndicator();
                    this.addBotMessage(data.message);
                    
                    if (data.speak && this.ttsEnabled) {
                        this.speak(data.message);
                    }
                    
                    if (data.language) {
                        this.updateLanguage(data.language);
                    }
                    break;
                
                case 'error':
                    this.hideTypingIndicator();
                    this.addSystemMessage(`❌ ${data.message}`);
                    break;
            }
        } catch (error) {
            console.error('Parse error:', error);
        }
    }

    speak(text) {
        this.synth.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        
        const voices = this.synth.getVoices();
        const englishVoice = voices.find(v => v.lang.startsWith('en'));
        if (englishVoice) {
            utterance.voice = englishVoice;
        }
        
        this.synth.speak(utterance);
    }

    toggleTTS() {
        this.ttsEnabled = !this.ttsEnabled;
        
        if (this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'toggle_tts',
                enabled: this.ttsEnabled
            }));
        }
        
        this.speakerBtn.textContent = this.ttsEnabled ? '🔊' : '🔇';
        this.speakerBtn.classList.toggle('muted', !this.ttsEnabled);
        
        this.addSystemMessage(
            this.ttsEnabled ? '🔊 Voice output enabled' : '🔇 Voice output disabled'
        );
    }

    sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message || !this.isConnected) return;

        this.addUserMessage(message);
        this.messageInput.value = '';
        this.showTypingIndicator();

        console.log('Sending:', message);
        this.ws.send(JSON.stringify({
            type: 'text',
            message: message
        }));
    }

    addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        messageDiv.innerHTML = `
            <div>
                <div class="message-content">${this.escapeHtml(text)}</div>
                <div class="message-time">${this.getCurrentTime()}</div>
            </div>
        `;
        this.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addBotMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';
        messageDiv.innerHTML = `
            <div>
                <div class="message-content">${this.escapeHtml(text)}</div>
                <div class="message-time">${this.getCurrentTime()}</div>
            </div>
        `;
        this.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addSystemMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'system-message';
        messageDiv.textContent = text;
        this.chatContainer.appendChild(messageDiv);
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
        return new Date().toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit'
        });
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const client = new DALIClient();
    console.log('✅ DALI Client with Voice Input initialized');
});
