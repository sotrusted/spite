import { logToBackend } from './modules/load_document_functions.js';
import { playSound, chatSounds } from './chat_sounds.js';
export class SpiteChat {
    constructor() {
        this.socket = null;
        this.messages = document.getElementById('chat-messages');
        this.input = document.getElementById('chat-input');
        this._connected = false;
        logToBackend('SpiteChat instance created', 'info');

        const soundToggle = document.querySelector('.sound-toggle');
        let soundEnabled = true;

        soundToggle.addEventListener('click', function() {
            soundEnabled = !soundEnabled;
            soundToggle.textContent = soundEnabled ? '🔊' : '🔇';
            soundToggle.classList.toggle('muted');
            
            // Update all sound volumes
            Object.values(chatSounds).forEach(sound => {
                sound.volume = soundEnabled ? 0.3 : 0;
            });
        });
    }

    // Establish WebSocket connection
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/chat/`;
        
        console.log('Attempting WebSocket connection to:', wsUrl);
        logToBackend(`Attempting chat WebSocket connection to: ${wsUrl}`, 'info');
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                this._connected = true;
                logToBackend('Chat WebSocket connection established', 'info');
                this.addSystemMessage('Connected to chat server');
            };

            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                logToBackend(`Chat message received: ${data.type}`, 'info');
                this.handleMessage(data);
            };

            this.socket.onclose = () => {
                this._connected = false;
                logToBackend('Chat WebSocket connection closed', 'warning');
                this.addSystemMessage('Disconnected from chat server');
            };

            this.socket.onerror = (error) => {
                this._connected = false;
                logToBackend(`Chat WebSocket error: ${error}`, 'error');
                this.addSystemMessage('Connection error - please try again');
            };
        } catch (error) {
            logToBackend(`Failed to create WebSocket connection: ${error}`, 'error');
            this.addSystemMessage('Failed to connect - please try again later');
        }
    }

    isConnected() {
        return this._connected && this.socket?.readyState === WebSocket.OPEN;
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this._connected = false;
        }
    }

    // Route different types of messages to appropriate handlers
    handleMessage(data) {
        switch(data.type) {
            case 'status':
                playSound('message');
                this.addSystemMessage(data.message, data.timestamp);
                break;
            case 'matched':
                playSound('join');
                this.addSystemMessage(data.message, data.timestamp);
                break;
            case 'disconnected':
                playSound('leave');
                this.addSystemMessage(data.message, data.timestamp);
                break;
            case 'message':
                playSound('message');
                this.addChatMessage(data.message, 'incoming', data.timestamp);
                break;
        }
    }

    // Add system messages (gray, centered) to chat
    addSystemMessage(message, timestamp = null) {
        const div = document.createElement('div');
        div.className = 'system-message';
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'chat-timestamp system';
        timeSpan.textContent = timestamp ? 
            new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}) :
            new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
        
        const messageSpan = document.createElement('span');
        messageSpan.className = 'chat-text';
        messageSpan.textContent = message;
        
        div.appendChild(timeSpan);
        div.appendChild(messageSpan);
        
        this.messages.appendChild(div);
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    // Add chat messages (left/right aligned) to chat
    addChatMessage(message, type = 'outgoing', timestamp = null) {
        const div = document.createElement('div');
        div.className = `chat-message ${type}`;
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'chat-timestamp';
        timeSpan.textContent = timestamp ? 
            new Date(timestamp).toLocaleTimeString([], {
                hour: 'numeric',
                minute: '2-digit',
                hour12: false
            }) :
            new Date().toLocaleTimeString([], {
                hour: 'numeric', 
                minute: '2-digit',
                hour12: false
            });
        
        const messageSpan = document.createElement('span');
        messageSpan.className = 'chat-text';
        messageSpan.textContent = message;
        
        div.appendChild(timeSpan);
        div.appendChild(messageSpan);
        
        this.messages.appendChild(div);
        this.messages.scrollTop = this.messages.scrollHeight;
    }

    // Send message to server via WebSocket
    sendMessage(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log('Sending message:', message);
            logToBackend(`Sending chat message: ${message.substring(0, 50)}...`, 'info');
            
            this.socket.send(JSON.stringify({
                type: 'message',
                message: message
            }));
            this.addChatMessage(message, 'outgoing');  // Add message to UI immediately
        } else {
            console.error('Cannot send message - socket not ready');
            logToBackend('Failed to send chat message - socket not ready', 'error');
        }
    }
}
