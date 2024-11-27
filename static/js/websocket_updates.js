// websocket_updates.py
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const socket = new WebSocket('wss://spite.fr/ws/posts/');
const notificationButton = document.getElementById("new-post-notification");
const notificationTitle = document.getElementById("new-post-title");
// Reference the notification sound element
const notificationSound = document.getElementById("notification-sound");


socket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    console.log(data);
    const post = data.message;

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

        attachCopyLinks();
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