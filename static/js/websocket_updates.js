// websocket_updates.pyww
import { addPostToPage, showNewPostNotification, updateSpiteCounter, 
    attachEventListeners, showNewCommentNotification, addCommentToPage } from './modules/utility_functions.js';

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
            showNewPostNotification(post, notificationTitle, notificationButton);

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