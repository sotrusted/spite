// websocket_updates.pyww
import { addPostToPage, showNewPostNotification, updateSpiteCounter, 
    attachEventListeners, showNewCommentNotification, addCommentToPage } from './modules/utility_functions.js';
import { logToBackend } from './modules/load_document_functions.js';
import { SpiteChat } from './chat.js';

export function initPostWebsocketUpdates() {
    // get protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

    const postSocket = new WebSocket('wss://spite.fr/ws/posts/');

    // Reference the notification sound element
    const notificationSound = document.getElementById("notification-sound");


    postSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        console.log(data);
        const post = data.post || data.message;

        // Check if the post already exists in the DOM
        if (!document.getElementById(`post-${post.id}`)) {
            // Post doesn't exist; add it to the page

            // Play the notification sound
            notificationSound.play();

            // Increment SPITE COUNTER
            updateSpiteCounter();

            // Display notification
            showNewPostNotification(post);

            // Add the post to the DOM
            addPostToPage(post);

            attachEventListeners();
            const button = document.getElementById(`toggle-comments-${post.id}`);
            button.addEventListener('click', function() {
                const commentsContainer = document.getElementById(`comments-container-${post.id}`);
                if (commentsContainer) {
                    commentsContainer.style.display = 
                        commentsContainer.style.display === 'none' ? 'block' : 'none';
                }
            });
        } else {
            console.log(`Post with ID ${post.id} already exists.`);
        }
    };

}

export function initCommentWebsocketUpdates() {
    // get protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

    const commentSocket = new WebSocket('wss://spite.fr/ws/comments/');

    // Reference the notification sound element
    const notificationSound = document.getElementById("notification-sound");

    commentSocket.onmessage = function (e) {
        const data = JSON.parse(e.data);
        console.log(data);
        const comment = data || data.comment || data.message;

        // Check if the post already exists in the DOM
        if (!document.getElementById(`comment-${comment.id}`)) {
            // Post doesn't exist; add it to the page

            // Play the notification sound
            notificationSound.play();

            // Increment SPITE COUNTER
            updateSpiteCounter();

            // Display notification
            showNewCommentNotification(comment);

            // Add the post to the DOM
            addCommentToPage(comment);

            // Attach event listeners
            attachEventListeners();

        } else {
            console.log(`Comment with ID ${comment.id} already exists.`);
        }
    };

}

export function initChatWebsocketUpdates() {
    let chat = null;
    const chatToggle = document.getElementById('chat-toggle');
    const chatContainer = document.getElementById('chat-container');
    
    if (chatToggle && chatContainer) {
        // Add mobile-friendly click/touch handler
        chatToggle.addEventListener('click', function(e) {
            e.preventDefault();  // Prevent double-tap zoom
            chatContainer.classList.toggle('hidden');
            
            if (!chatContainer.classList.contains('hidden')) {
                if (!chat) {
                    chat = new SpiteChat();
                    chat.connect();
                }
                // On mobile, ensure chat is visible
                if (window.innerWidth <= 768) {
                    window.scrollTo(0, document.body.scrollHeight);
                }
            }
        });

        // Add close button handler
        const closeButton = document.querySelector('.close-chat-btn');
        if (closeButton) {
            closeButton.addEventListener('click', function() {
                chatContainer.classList.add('hidden');
                if (chat) {
                    chat.disconnect();
                    chat = null;
                }
            });
        }

        // Handle send message
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.querySelector('.send-message-btn');
        
        function sendChatMessage() {
            if (chat && chatInput) {
                const message = chatInput.value.trim();
                if (message) {
                    chat.sendMessage(message);
                    chatInput.value = '';
                }
            }
        }

        if (chatInput) {
            chatInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    sendChatMessage();
                }
            });
        }

        if (sendButton) {
            sendButton.addEventListener('click', function(e) {
                e.preventDefault();
                sendChatMessage();
            });
        }

        // Handle new chat button
        const newChatBtn = document.querySelector('.new-chat-btn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', function() {
                if (chat) {
                    chat.socket.close();
                    document.getElementById('chat-messages').innerHTML = '';
                    chat.connect();
                }
            });
        }

        // Add maximize button handler
        const maximizeButton = document.querySelector('.maximize-chat-btn');
        if (maximizeButton) {
            maximizeButton.addEventListener('click', function() {
                chatContainer.classList.toggle('maximized');
                // Update button text based on state
                this.textContent = chatContainer.classList.contains('maximized') ? '❐' : '□';
                
                // Focus input when maximized
                if (chatContainer.classList.contains('maximized')) {
                    document.getElementById('chat-input')?.focus();
                }
            });
        }

        logToBackend('Chat controls initialized', 'info');
    }
}