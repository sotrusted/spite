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
        this.apiUrl = root.dataset.ragbotHttpUrl || '/api/ragbot/chat/';
        this.streamUrl = root.dataset.ragbotStreamUrl || '/api/ragbot/chat/stream/';
        this.logUrl = root.dataset.ragbotLogUrl || '/api/ragbot/log/';
        this.shareUrl = root.dataset.shareUrl;
        this.messagesEl = root.querySelector('[data-ragbot-messages]');
        this.inputEl = root.querySelector('[data-ragbot-input]');
        this.formEl = root.querySelector('[data-ragbot-form]');
        this.statusEl = root.querySelector('[data-ragbot-status]');
        this.clearBtnEl = root.querySelector('[data-ragbot-clear]');
        this.shareBtnEl = root.querySelector('[data-ragbot-share]');
        this.streamingAvailable = true; // Try streaming first, fallback if it fails
        this.currentCitations = [];
        this.currentMessageElement = null;
        this.chatHistory = []; // Store conversation history
        
        // Token throttling for smooth streaming display
        this.tokenQueue = [];
        this.isProcessingQueue = false;
        this.streamingDelay = 50; // milliseconds between tokens (adjust for speed)
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

        if (this.clearBtnEl) {
            this.clearBtnEl.addEventListener('click', () => {
                this.clearHistory();
            });
        }

        if (this.shareBtnEl) {
            this.shareBtnEl.addEventListener('click', () => {
                this.shareChat();
            });
        }

        // Show welcome message from Jayden
        this.showWelcomeMessage();

        if (this.socketUrl) {
            this.connect();
        } else {
            this.setStatus('Ready');
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

        // Add user message to history
        this.addToHistory('user', content);

        this.appendChatMessage('You', content, 'outgoing');
        this.inputEl.value = '';
        this.logExchange({ direction: 'outgoing', message: content });

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.sendWebSocketMessage(content);
        } else if (this.streamingAvailable) {
            this.sendStreamingMessage(content);
        } else {
            this.sendHttpMessage(content);
        }
    }

    addToHistory(role, content) {
        this.chatHistory.push({
            role: role, // 'user' or 'assistant'
            content: content
        });
        
        // Keep only last 20 messages to avoid sending too much data
        if (this.chatHistory.length > 20) {
            this.chatHistory = this.chatHistory.slice(-20);
        }
    }

    formatChatHistory() {
        // Format history as expected by the RAG service
        // You may need to adjust this format based on what the service expects
        return this.chatHistory.map(msg => `${msg.role}: ${msg.content}`).join('\n');
    }

    clearHistory() {
        // Clear chat history
        this.chatHistory = [];
        
        // Clear UI messages
        if (this.messagesEl) {
            this.messagesEl.innerHTML = '';
        }
        
        // Add confirmation message
        this.appendSystemMessage('Chat history cleared. Starting fresh conversation.');
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
                body: JSON.stringify({ 
                    query: message,
                    chat_history: this.formatChatHistory()
                }),
                mode: 'cors',
            });

            if (!response.ok) {
                console.error(`Regular request failed with status ${response.status}: ${response.statusText}`);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
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
            this.setStatus(this.socket && this.socket.readyState === WebSocket.OPEN ? 'Connected' : 'Ready');
        }
    }

    async sendStreamingMessage(message) {
        if (!this.streamUrl) {
            this.appendSystemMessage('RAG bot streaming endpoint not configured.');
            return;
        }

        this.setStatus('Streaming response…');
        this.currentCitations = [];
        this.currentMessageElement = null;
        
        try {
            console.log('Sending streaming message to', this.streamUrl);
            const csrfToken = getCookie('csrftoken');
            const headers = {
                'Content-Type': 'application/json',
            };
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }
            
            const response = await fetch(this.streamUrl, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ 
                    query: message,
                    chat_history: this.formatChatHistory()
                }),
                credentials: 'same-origin',
            });

            if (!response.ok) {
                console.error(`Streaming request failed with status ${response.status}: ${response.statusText}`);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let hasReceivedData = false;

            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    // Stream completed - finalize the message if we have one
                    if (this.currentMessageElement && hasReceivedData) {
                        this.handleStreamingData({ done: true });
                    }
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop(); // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonStr = line.substring(6);
                            console.log('Parsing streaming data:', jsonStr);
                            
                            // Try to parse as JSON first
                            let data;
                            try {
                                data = JSON.parse(jsonStr);
                            } catch (parseError) {
                                // If not JSON, treat as plain text content
                                data = jsonStr;
                            }
                            
                            this.handleStreamingData(data);
                            hasReceivedData = true;
                        } catch (e) {
                            console.warn('Failed to handle streaming data:', line, 'Error:', e);
                        }
                    } else if (line.trim()) {
                        console.log('Non-data line received:', line);
                    }
                }
            }
        } catch (error) {
            console.error('Failed to stream ragbot response', error);
            this.streamingAvailable = false;
            this.appendSystemMessage('Streaming failed, falling back to regular mode...');
            // Retry with regular HTTP
            this.sendHttpMessage(message);
        } finally {
            this.setStatus(this.socket && this.socket.readyState === WebSocket.OPEN ? 'Connected' : 'Ready');
        }
    }

    handleStreamingData(data) {
        // Handle error objects
        if (typeof data === 'object' && data.error) {
            this.appendSystemMessage(`Error: ${data.error}`);
            return;
        }

        // Handle citations objects
        if (typeof data === 'object' && data.citations) {
            console.log('Citations:', data.citations);
            this.currentCitations = data.citations;
            return;
        }

        // Handle done signal
        if (typeof data === 'object' && data.done) {
            // Wait for all queued tokens to finish displaying before finalizing
            this.finalizeStreamingMessage();
            return;
        }

        // Handle content - either as object with content field or direct string
        let content = null;
        if (typeof data === 'object' && data.content) {
            content = data.content;
        } else if (typeof data === 'string') {
            // Direct string content from RAG bot
            content = data;
        }

        if (content) {
            if (!this.currentMessageElement) {
                this.currentMessageElement = this.createStreamingMessage();
            }
            // Add content to queue for throttled display
            this.queueTokens(content);
            return;
        }

        // Log unexpected data format for debugging
        console.log('Unexpected streaming data format:', data);
    }

    queueTokens(content) {
        // Add the content chunk to queue (already tokenized by the server)
        this.tokenQueue.push(content);
        
        // Start processing queue if not already running
        if (!this.isProcessingQueue) {
            this.processTokenQueue();
        }
    }

    async processTokenQueue() {
        this.isProcessingQueue = true;
        
        while (this.tokenQueue.length > 0) {
            const token = this.tokenQueue.shift();
            this.appendContentToStreamingMessage(token);
            
            // Wait before processing next token (throttling)
            await new Promise(resolve => setTimeout(resolve, this.streamingDelay));
        }
        
        this.isProcessingQueue = false;
    }

    async finalizeStreamingMessage() {
        // Wait for all tokens in queue to be processed
        while (this.tokenQueue.length > 0 || this.isProcessingQueue) {
            await new Promise(resolve => setTimeout(resolve, 10));
        }
        
        if (this.currentMessageElement) {
            // Remove streaming indicator
            this.currentMessageElement.classList.remove('streaming');
            const indicator = this.currentMessageElement.querySelector('.streaming-indicator');
            if (indicator) {
                indicator.remove();
            }
            
            // Add citations if present
            if (this.currentCitations.length > 0) {
                this.addCitationsToMessage(this.currentMessageElement, this.currentCitations);
            }
            
            // Get the complete response text
            const responseText = this.currentMessageElement.querySelector('.ragbot-message__body')?.textContent || '[streaming completed]';
            
            // Add assistant response to history
            this.addToHistory('assistant', responseText);
            
            this.logExchange({ 
                direction: 'incoming', 
                message: responseText,
                citations: this.currentCitations
            });
        }
        this.currentMessageElement = null;
        this.currentCitations = [];
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

        const citations = payload?.citations || [];
        this.appendChatMessage('Spite RAG', text, 'incoming', citations);
        this.logExchange({ direction: 'incoming', message: text, citations });
        
        // Add assistant response to history
        this.addToHistory('assistant', text);
    }

    createStreamingMessage() {
        const wrapper = document.createElement('div');
        wrapper.className = 'ragbot-message incoming streaming';

        const header = document.createElement('div');
        header.className = 'ragbot-message__meta';
        header.innerHTML = `Spite RAG • ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} <span class="streaming-indicator">●</span>`;

        const body = document.createElement('div');
        body.className = 'ragbot-message__body';
        body.textContent = '';

        wrapper.appendChild(header);
        wrapper.appendChild(body);

        this.messagesEl.appendChild(wrapper);
        this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
        
        return wrapper;
    }

    appendContentToStreamingMessage(content) {
        if (!this.currentMessageElement) return;
        
        const body = this.currentMessageElement.querySelector('.ragbot-message__body');
        if (body) {
            body.textContent += content;
            this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
        }
    }

    addCitationsToMessage(messageElement, citations) {
        if (!citations || citations.length === 0) return;

        const citationsContainer = document.createElement('div');
        citationsContainer.className = 'ragbot-citations';
        
        const citationsTitle = document.createElement('div');
        citationsTitle.className = 'ragbot-citations__title';
        citationsTitle.textContent = 'Sources:';
        citationsContainer.appendChild(citationsTitle);

        citations.forEach(citation => {
            const citationEl = document.createElement('div');
            citationEl.className = 'ragbot-citation';
            
            const citationLink = document.createElement('a');
            citationLink.href = citation.url;
            citationLink.target = '_blank';
            citationLink.className = 'ragbot-citation__link';
            
            if (citation.type === 'post') {
                citationLink.innerHTML = `
                    <span class="ragbot-citation__number">[${citation.citation_number}]</span>
                    <span class="ragbot-citation__title">${citation.title}</span>
                    ${citation.display_name || citation.author ? `<span class="ragbot-citation__author">by ${citation.display_name || citation.author}</span>` : ''}
                    ${citation.content ? `<span class="ragbot-citation__content">${citation.content}</span>` : ''}
                `;
            } else if (citation.type === 'comment') {
                citationLink.innerHTML = `
                    <span class="ragbot-citation__number">[${citation.citation_number}]</span>
                    ${citation.name ? `<span class="ragbot-citation__title">${citation.name}</span>` : ''}
                    ${citation.content ? `<span class="ragbot-citation__content">${citation.content}</span>` : ''}
                    <span class="ragbot-citation__meta">on post #${citation.post_id}</span>
                `;
            }
            
            citationEl.appendChild(citationLink);
            citationsContainer.appendChild(citationEl);
        });

        messageElement.appendChild(citationsContainer);
    }

    appendChatMessage(author, text, variant, citations = []) {
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

        // Add citations if present
        if (citations && citations.length > 0) {
            this.addCitationsToMessage(wrapper, citations);
        }

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

    showWelcomeMessage() {
        // Check if there are already messages to avoid showing welcome multiple times
        if (this.messagesEl && this.messagesEl.children.length === 0) {
            const welcomeText = "Hi I'm Jayden! You can ask me any questions about Spite Magazine characters and use me to find posts.";
            this.appendChatMessage('Jayden', welcomeText, 'incoming', []);
        }
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

    async shareChat() {
        if (!this.shareUrl) {
            this.appendSystemMessage('Share functionality not available.');
            return;
        }

        // Check if there are any messages to share
        if (this.chatHistory.length === 0) {
            this.appendSystemMessage('No messages to share. Start a conversation first!');
            return;
        }

        // Try to copy the share URL to clipboard
        try {
            await navigator.clipboard.writeText(this.shareUrl);
            this.appendSystemMessage('Share link copied to clipboard!');
        } catch (error) {
            // Fallback: show the URL for manual copying
            this.appendSystemMessage(`Share this conversation: ${this.shareUrl}`);
        }
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
