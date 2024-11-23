function updateSpiteCounter() {
    const counterElement = document.getElementById("spite-counter");
    const currentCount = parseInt(counterElement.textContent.split(":")[1].trim());
    counterElement.textContent = `SPITE COUNTER: ${currentCount + 1}`;
}

// Function to show the notification
function showNewPostNotification(message) {
    notificationTitle.textContent = `${message.title.substring(0, 20)}...`;
    notificationButton.style.display = "block";

    // Scroll to the post when the button is clicked
    notificationButton.onclick = function () {
        const newPostElement = document.getElementById(`post-${message.id}`);
        if (newPostElement) {
            // Scroll slightly above the newly added post
            const newPostPosition = newPostElement.getBoundingClientRect().top + window.scrollY;
            const offset = 100; // Adjust this value for desired spacing
            window.scrollTo({
                top: newPostPosition - offset,
                behavior: 'smooth'
            });
            // Hide the notification after clicking
            notificationButton.style.display = "none";
        };
    };

    setTimeout(() => {
        notificationButton.style.display = "none";
    }, 10000); // Hide after 10 seconds
}


function addPostToPage(post) {
    const postList = document.getElementById('post-list');

    const newPost = document.createElement('div');
    newPost.classList.add('item');

    const postId = post.id;
    newPost.id = `post-${postId}`;

    newPost.innerHTML = `
        <div class="preview" id="post-preview-${postId}">
            <div class="post flexbox">
                <div class="text-content">
                    <h2 class="post-title">
                        <a href="/post/${postId}/">
                            ${post.title}
                        </a>
                    </h2>
                    ${post.parent_post ? `<p>Replying to: <a href="/post/${post.parent_post.id}/">${post.parent_post.title}</a></p>` : ''}
                    <div class="post-content">
                        ${post.content ? `<p>${post.content}</p>` : ''}
                    </div>
                    <div class="menu">
                        <a href="javascript:void(0);" class="toggle-link" id="toggle-link-${postId}" onclick="toggleContent(${postId})">Expand</a>
                        <a href="javascript:void(0);" id="copy-link-{{post.id}}" class="share-btn copy-link">Copy Link</a>
                    </div>
                    ${post.author ? `<p class="post-author">by ${post.author}</p>` : ''}
                    <p class="post-date">${post.date_posted}</p>
                    ${post.city || post.contact ? `
                        <p class="post-info">
                            ${post.city ? post.city : ''}${post.city && post.contact ? ' / ' : ''}${post.contact ? post.contact : ''}
                        </p>` : ''}
                </div>
                ${post.media_file || post.image ? `
                <div class="image-content">
                    <div class="image-container">
                        <a href="/post/${postId}/">
                            ${post.media_file && post.is_video ? `
                                <video autoplay muted loop playsinline>
                                    <source src="${post.media_file.url}" type="video/mp4">
                                </video>` : ''}
                            ${post.media_file && post.is_image ? `<img src="${post.media_file.url}" alt="${post.title}" loading="lazy">` : ''}
                            ${post.image ? `<img src="${post.image.url}" alt="${post.title}" loading="lazy">` : ''}
                        </a>
                    </div>
                </div>` : ''}
            </div>
        </div>
        <div class="detail" id="post-detail-${postId}" style="display: none;">
            <div class="post flexbox">
                ${post.media_file || post.image ? `
                <div class="image-content">
                    <div class="image-container">
                        ${post.media_file && post.is_video ? `
                            <video controls muted autoplay playsinline>
                                <source src="${post.media_file}" type="video/mp4">
                            </video>` : ''}
                        ${post.media_file && post.is_image ? `<img src="${post.media_file}" alt="${post.title}" loading="lazy">` : ''}
                        ${post.image ? `<img src="${post.image}" alt="${post.title}" loading="lazy">` : ''}
                    </div>
                </div>` : ''}
                <div class="text-content">
                    <h1 class="post-title">${post.title}</h1>
                    ${post.parent_post ? `<p>Replying to: <a href="/post/${post.parent_post.id}/">${post.parent_post.title}</a></p>` : ''}
                    <div class="post-content">
                        <p>${post.content}</p>
                    </div>
                    ${post.author ? `<p class="post-author">by ${post.author}</p>` : `<p class="post-author">by Anonymous ${post.anon_uuid}</p>`}
                    <p class="post-date">${post.date_posted}</p>
                </div>
                <div class="menu">
                    <a href="javascript:void(0);" class="toggle-link" id="toggle-link-${postId}" onclick="toggleContent(${postId})">Expand</a>
                    <a href="javascript:void(0);" id="copy-link-{{post.id}}" class="share-btn copy-link">Copy Link</a>
                </div>
            </div>
        </div>
        <div id="comment-section-${postId}">
            <button id="toggle-comments-${postId}" class="toggle-comments" post-id="${postId}">
                Comments (0)
            </button>
            <div id="comments-container-${postId}" class="comments-container" style="display: none;">
                <div id="comments-list-${postId}">
                    <p>No comments yet.</p>
                </div>
                <form id="comment-form-${postId}" method="post" action="/add-comment/${postId}/">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${getCookie('csrftoken')}">
                    <textarea name="content" class="form-control" placeholder="Write your comment here..." required></textarea>
                    <button type="submit">Submit</button>
                </form>
            </div>
        </div>
    `;
    postList.prepend(newPost); // Add the new post to the top of the list

    newPost.classList.add("highlight");
    setTimeout(() => newPost.classList.remove("highlight"), 3000); // Remove after 3 seconds

    attachEventListeners();
    attachCopyLinks();
    return newPost;
}