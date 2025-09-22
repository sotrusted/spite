import { getCookie } from './modules/load_document_functions.js';

function createUuid() {
    if (window.crypto?.randomUUID) {
        return window.crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function buildWebSocketUrl(rawUrl) {
    if (!rawUrl) {
        return null;
    }

    if (/^wss?:/i.test(rawUrl)) {
        return rawUrl;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const trimmed = rawUrl.startsWith('/') ? rawUrl : `/${rawUrl}`;
    return `${protocol}//${window.location.host}${trimmed}`;
}

class RagbotChatClient {
    constructor(root) {
        this.root = root;
        this.socket = null;
        this.sessionId = root.dataset.sessionId || createUuid();
        this.socketUrl = buildWebSocketUrl(root.dataset.ragbotWsUrl || '');
        this.apiUrl = root.dataset.ragbotHttpUrl || '/api/ragbot/chat';
        this.logUrl = root.dataset.ragbotLogUrl || '/api/ragbot/log/';
        this.messagesEl = root.querySelector('[data-ragbot-messages]');
        this.inputEl = root.querySelector('[data-ragbot-input]');
        this.formEl = root.querySelector('[data-ragbot-form]');
        this.statusEl = root.querySelector('[data-ragbot-status]');
    }

    init() {
        if (!this.formEl || !this.inputEl || !this.messagesEl) {
            console.warn('Ragbot chat missing required elements');
            return;
        }

        this.formEl.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleSend();
        });

        this.inputEl.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.handleSend();
            }
        });

        if (this.socketUrl) {
            this.connect();
        } else {
            this.setStatus('HTTP mode');
            this.appendSystemMessage('Using HTTP endpoint.');
        }
    }

    connect() {
        if (!this.socketUrl) {
            this.appendSystemMessage('Missing RAG bot endpoint.');
            return;
        }

        try {
            this.socket = new WebSocket(this.socketUrl);
        } catch (error) {
            console.error('Failed to connect to RAG bot WebSocket', error);
            this.appendSystemMessage('Unable to connect to RAG bot.');
            return;
        }

        this.socket.addEventListener('open', () => {
            this.setStatus('Connected');
            this.appendSystemMessage('Connected to RAG bot.');
        });

        this.socket.addEventListener('message', (event) => {
            this.handleIncoming(event.data);
        });

        this.socket.addEventListener('close', () => {
            this.setStatus('Disconnected');
            this.appendSystemMessage('Connection closed.');
        });

        this.socket.addEventListener('error', (error) => {
            console.error('Ragbot socket error', error);
            this.appendSystemMessage('Connection error encountered.');
        });
    }

    setStatus(text) {
        if (this.statusEl) {
            this.statusEl.textContent = text;
        }
    }

    handleSend() {
        const content = this.inputEl.value.trim();
        if (!content) {
            return;
        }

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.sendWebSocketMessage(content);
        } else {
            this.sendHttpMessage(content);
        }
        this.appendChatMessage('You', content, 'outgoing');
        this.inputEl.value = '';
        this.logExchange({ direction: 'outgoing', message: content });
    }

    sendWebSocketMessage(message) {
        try {
            this.socket.send(JSON.stringify({ message, session_id: this.sessionId }));
        } catch (error) {
            console.error('Failed to send message to RAG bot', error);
            this.appendSystemMessage('Failed to send message.');
        }
    }

    async sendHttpMessage(message) {
        if (!this.apiUrl) {
            this.appendSystemMessage('RAG bot HTTP endpoint not configured.');
            return;
        }

        this.setStatus('Awaiting response…');
        try {
            console.log('Sending HTTP message to', this.apiUrl);
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: message }),
                mode: 'cors',
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const contentType = response.headers.get('content-type') || '';
            let payload;
            if (contentType.includes('application/json')) {
                payload = await response.json();
            } else {
                payload = await response.text();
            }

            this.processBotPayload(payload);
        } catch (error) {
            console.error('Failed to fetch ragbot response', error);
            this.appendSystemMessage('Failed to reach RAG bot HTTP endpoint.');
        } finally {
            this.setStatus(this.socket && this.socket.readyState === WebSocket.OPEN ? 'Connected' : 'Idle');
        }
    }

    handleIncoming(raw) {
        let payload = raw;
        try {
            payload = JSON.parse(raw);
        } catch (_error) {
            // fall back to plain text payloads
        }

        this.processBotPayload(payload);
    }

    processBotPayload(payload) {
        let text = typeof payload === 'string'
            ? payload
            : (payload?.response || payload?.message || payload?.answer || payload?.data || JSON.stringify(payload));

        if (!text) {
            text = '[no response]';
        }

        this.appendChatMessage('Spite RAG', text, 'incoming');
        this.logExchange({ direction: 'incoming', message: text });
    }

    appendChatMessage(author, text, variant) {
        if (!this.messagesEl) {
            return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = `ragbot-message ${variant}`;

        const header = document.createElement('div');
        header.className = 'ragbot-message__meta';
        header.textContent = `${author} • ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

        const body = document.createElement('div');
        body.className = 'ragbot-message__body';
        body.textContent = text;

        wrapper.appendChild(header);
        wrapper.appendChild(body);

        this.messagesEl.appendChild(wrapper);
        this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    }

    appendSystemMessage(text) {
        if (!this.messagesEl) {
            return;
        }
        const node = document.createElement('div');
        node.className = 'ragbot-message system';
        node.textContent = text;
        this.messagesEl.appendChild(node);
        this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    }

    logExchange(entry) {
        const csrfToken = getCookie('csrftoken');
        if (!this.logUrl || !csrfToken) {
            return;
        }

        fetch(this.logUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                session_id: this.sessionId,
                entry,
            }),
            credentials: 'same-origin',
        }).catch((error) => {
            console.warn('Failed to log ragbot exchange', error);
        });
    }
}

function bootRagbotChat() {
    const root = document.querySelector('[data-ragbot-chat-root]');
    if (!root) {
        return;
    }

    const client = new RagbotChatClient(root);
    client.init();
}

if (document.readyState === 'complete' || document.readyState === 'interactive') {
    bootRagbotChat();
} else {
    document.addEventListener('DOMContentLoaded', bootRagbotChat);
}

export default RagbotChatClient;
