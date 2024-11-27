function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

async function refreshCSRFToken() {
    const response = await fetch('/get-csrf-token/');
    const data = await response.json();
    document.querySelector('[name=csrfmiddlewaretoken]').value = data.csrfToken;
}

// Function to toggle content between detail and preview
function toggleContent(postId) {
    var detailDiv = document.getElementById('post-detail-' + postId);
    var previewDiv = document.getElementById('post-preview-' + postId);
    var toggleButton = document.getElementById('toggle-link-' + postId); 
    if (detailDiv.style.display === 'none') {
        detailDiv.style.display = 'flex';
        previewDiv.style.display = 'none';
        toggleButton.textContent = 'Collapse';
    } else {
        detailDiv.style.display = 'none';
        previewDiv.style.display = 'flex';
        toggleButton.textContent = 'Expand';
    }
}

//Function to attach event listeners to copy links
function attachCopyLinks() {
    document.querySelectorAll('a[id^="copy-link-"]').forEach(a => {
        a.addEventListener('click', function () {
            // Extract the post ID from the link's ID attribute
            const postId = this.id.replace('copy-link-', ''); // e.g., 'copy-link-123' -> '123'

            // Construct the URL dynamically
            const link = `https://spite.fr/post/${postId}`;

            // Copy the link to the clipboard
            navigator.clipboard.writeText(link).then(() => {
                // Optional: Show a confirmation message
                const message = document.createElement('span');
                message.textContent = 'Link copied!';
                message.style.color = 'green';
                this.parentElement.appendChild(message);

                // Remove the message after 2 seconds
                setTimeout(() => {
                    message.remove();
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy link:', err);
                alert('Failed to copy the link. Please try again.');
            });
        })
    })
}

// Attach submit event to all comment forms
function attachEventListeners() {
    document.querySelectorAll('form[id^="comment-form-"]').forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault(); // Prevent default form submission

            const formData = new FormData(this);
            const postId = this.id.split('-').pop(); // Extract post ID from form ID
            const url = this.action; // Form action URL

            // Perform AJAX request
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken'), // Include CSRF token
                },
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Clear the form
                    this.reset();

                    // Append the new comment to the comment list
                    const commentList = document.getElementById(`comments-list-${postId}`);
                    const newComment = document.createElement('div');
                    newComment.classList.add('comment');
                    newComment.innerHTML = `
                        <strong>${data.comment.name || 'Anonymous'}</strong>: ${data.comment.content}
                        <p><em>${data.comment.created_on}</em></p>
                    `;
                    commentList.appendChild(newComment);

                    // Make sure the comments container is visible
                    const commentsContainer = document.getElementById(`comments-container-${postId}`);
                    commentsContainer.style.display = 'block';
                } else {
                    alert('Failed to add comment. Please try again.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while adding the comment.');
            });
        });
    });


    // Automatically expand comments if data-has-comments is true
    console.log("Expanding comments...");
    document.querySelectorAll('.comments-container').forEach(container => {
        const hasComments = container.dataset.hasComments === 'true';
        console.log(hasComments);

        if (hasComments) {
            container.style.display = 'block';
            console.log('Expanded');
        }
    });

    // Add click listeners for toggling comments
    document.querySelectorAll('.toggle-comments').forEach(button => {
        button.addEventListener('click', function() {
            const postId = this.dataset.postId;
            const commentsContainer = document.getElementById(`comments-container-${postId}`);
            if (commentsContainer) {
                commentsContainer.style.display = 
                    commentsContainer.style.display === 'none' ? 'block' : 'none';
            }
        });
    });
}; 


function disableSubmitButton() {
    var submitButton = document.getElementById('submit-id-submit');
    console.log(submitButton.value);
    submitButton.disabled = true;
    submitButton.value = 'Posting...';  // Change the button text
}
function enableSubmitButton() {
    var submitButton = document.getElementById('submit-id-submit');
    submitButton.disabled = false;
    submitButton.value = 'Post';  // Change the button text
}


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
                    ${post.display_name ? `<p class="post-author">by ${post.display_name}</p>` : `<p class="post-author">by Anonymous ${post.anon_uuid}</p>`}
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



