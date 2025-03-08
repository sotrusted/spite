import { logToBackend } from './modules/load_document_functions.js';
import { playSound, chatSounds } from './chat_sounds.js';
export class SpiteChat {
    constructor() {
        this.socket = null;
        this.messages = document.getElementById('chat-messages');
        this.input = document.getElementById('chat-input');
        this._connected = false;
        logToBackend('SpiteChat instance created', 'info');

        const soundToggle = document.querySelector('.chat-sound-toggle');
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
                console.log('WebSocket connection established');
                this._connected = true;
                logToBackend('Chat WebSocket connection established', 'info');
                
                // Log the state of the user count element
                const userCountElement = document.querySelector('.chat-toggle-btn .user-count');
                console.log('User count element on connection:', userCountElement);
                console.log('Chat toggle button HTML:', document.querySelector('.chat-toggle-btn')?.innerHTML);
                
                this.addSystemMessage('Connected to chat server');
            };

            this.socket.onmessage = (event) => {
                console.log('Raw WebSocket message:', event.data);
                const data = JSON.parse(event.data);
                console.log('Parsed WebSocket message:', data);
                logToBackend(`Chat message received: ${data.type}`, 'info');
                this.handleMessage(data);
            };

            this.socket.onclose = () => {
                console.log('WebSocket connection closed');
                this._connected = false;
                logToBackend('Chat WebSocket connection closed', 'warning');
                this.addSystemMessage('Disconnected from chat server');
            };

            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this._connected = false;
                logToBackend(`Chat WebSocket error: ${error}`, 'error');
                this.addSystemMessage('Connection error - please try again');
            };
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
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
        console.log('Handling message type:', data.type);
        switch(data.type) {
            case 'status':
                console.log('Handling status message:', data.message);
                playSound('message');
                this.addSystemMessage(data.message, data.timestamp);
                break;
            case 'matched':
                console.log('Handling matched message:', data.message);
                playSound('join');
                this.addSystemMessage(data.message, data.timestamp);
                break;
            case 'disconnected':
                console.log('Handling disconnected message:', data.message);
                playSound('leave');
                this.addSystemMessage(data.message, data.timestamp);
                break;
            case 'message':
                console.log('Handling chat message:', data.message);
                playSound('message');
                this.addChatMessage(data.message, 'incoming', data.timestamp);
                break;
            case 'user_count':
                console.log('Handling user count update. Count:', data.count);
                const userCountElement = document.querySelector('.chat-toggle-btn .user-count');
                if (userCountElement) {
                    console.log('Found user count element, updating to:', data.count);
                    userCountElement.textContent = data.count;
                } else {
                    console.warn('User count element not found in DOM');
                    console.log('Current DOM structure:', document.querySelector('.chat-toggle-btn')?.innerHTML);
                }
                break;
            default:
                console.warn('Unknown message type:', data.type);
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
