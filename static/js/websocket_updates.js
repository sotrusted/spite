// websocket_updates.py
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const socket = new WebSocket('wss://spite.fr/ws/posts/');
const notificationButton = document.getElementById("new-post-notification");
const notificationTitle = document.getElementById("new-post-title");


socket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    console.log(data);
    const post = data.message;

    // Check if the post already exists in the DOM
    if (!document.getElementById(`post-${post.id}`)) {
        // Post doesn't exist; add it to the page

        // Increment SPITE COUNTER
        updateSpiteCounter();
        // Display notification
        showNewPostNotification(post);
        // Add the post to the DOM
        addPostToPage(post);
    } else {
        console.log(`Post with ID ${post.id} already exists.`);
    }
};