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

// Helper function to set a cookie
function setCookie(name, value, days) {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
}


// Function to save input and hide the modal
function saveInput() {
    // Select all input elements with the class or ID "user-input"
    const inputs = document.querySelectorAll("#user-input, .user-input"); // Adjust selectors as needed

    let userInput = null;

    // Loop through inputs and find the one with a value
    inputs.forEach(input => {
        if (input.value.trim()) {
            userInput = input.value.trim(); // Get the value
        }
    });
    

    if (!userInput) {
        alert("Please enter something before proceeding.");
        return;
    }

    // Save input via the API
    fetch('/api/save-list/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ input: userInput }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log("Input saved:", data);
                setCookie("input_shown", "true", 365); // Prevent the modal from showing again
                document.getElementById("modal-overlay").style.display = "none";
                document.body.classList.remove("modal-active"); // Re-enable scrolling
                inputs.forEach(input => {
                    if (input.value.trim()) {
                        input.value = ''; // Clear only the input that was used
                    }
                })
            } else {
                console.error("Error saving input:", data.error);
            }
        })
        .catch(error => console.error("API Error:", error));
}


//Function to load word cloud
function loadWordCloud() {
    fetch('/api/word-cloud/')
        .then(response => response.json())
        .then(data => {
            const wordCloud = document.getElementById('word-cloud');
            wordCloud.innerHTML = ''; // Clear existing words

            data.entries.forEach(entry => {
                const wordElement = document.createElement('span');
                wordElement.className = 'word';
                wordElement.textContent = entry;
                wordCloud.appendChild(wordElement);
            });
        })
        .catch(error => console.error('Error fetching word cloud:', error));
}


// Function to show the modal if the cookie is not set
function showModalIfNeeded() {
    const alreadyShown = getCookie("input_shown");
    console.log("Input shown: " + alreadyShown);
    if (!alreadyShown) {
        document.getElementById("modal-overlay").style.display = "flex";
        document.body.classList.add("modal-active"); // Disable scrolling
        // loadWordCloud(); // Load word cloud
    }
    else {
        document.getElementById("modal-overlay").style.display = "none";
        document.body.classList.remove("modal-active");
    }
}



// Function to refresh the csrf token in the DOM 
async function refreshCSRFToken() {
    try {
        const response = await fetch('/get-csrf-token/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        document.querySelector('[name=csrfmiddlewaretoken]').value = data.csrfToken;
    } catch (error) {
        console.error("Error refreshing CSRF token:", error);
    }
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

function attachToggleReplyButtons() {
    document.querySelectorAll('a[id^="toggle-reply-"]').forEach(a => {
        a.addEventListener('click', function() {
            const postId = this.id.split('-').pop(); // Extract the part after the last '-'
            console.log(postId);
            const commentReplyForm  = document.querySelector(`div[id^=reply-form-${postId}]`);
            console.log(commentReplyForm);
            if (commentReplyForm) {
                console.log(`Reply form for comment ${postId} toggled`)
                commentReplyForm.style.display = 
                    commentReplyForm.style.display === 'none' ? 'block' : 'none';
            } else {
                console.error(`Reply form for comment ${postId} not found`)
            }
        })
    })
}

// Function to attach event listeners to copy links
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


    setWriteLinksScrollers();

    document.querySelectorAll('#feed-scroller').forEach(a => {
       a.addEventListener('click', function() {
            scrollToElementById('recent-posts');
       });
    });


    attachToggleReplyButtons();


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


// Function to show the notification
function showNewCommentNotification(message) {
    commentNotificationTitle.textContent = `${message.post_title.substring(0, 20)}...`;
    commentNotificationButton.style.display = "block";
    // Scroll to the post when the button is clicked
    commentNotificationButton.onclick = function () {
        const newCommentElement = document.getElementById(`comment-${message.id}`);
        if (newCommentElement) {
            // Scroll slightly above the newly added post
            const newCommentPosition = newCommentElement.getBoundingClientRect().top + window.scrollY;
            const offset = 100; // Adjust this value for desired spacing
            window.scrollTo({
                top: newCommentPosition - offset,
                behavior: 'smooth'
            });
            // Hide the notification after clicking
            commentNotificationButton.style.display = "none";
        };
    };

    setTimeout(() => {
        commentNotificationButton.style.display = "none";
    }, 10000); // Hide after 10 seconds
}

function scrollToElementById(id) {
    const targetElement = document.getElementById(id);
    const targetPosition = targetElement.getBoundingClientRect().top + window.scrollY;
    const offset = 100; // Adjust this value for desired spacing
    console.log(targetPosition - offset)
    window.scrollTo({
        top: targetPosition - offset,
    });
}

function setWriteLinksScrollers() {
    document.querySelectorAll('.post-link').forEach(a => {
        a.addEventListener('click', function () {
            scrollToElementById('post-form');
        });
    });
}


function addPostToPage(post) {
    const postList = document.getElementById('post-list');

    const newPost = document.createElement('div');
    newPost.classList.add('item');
    newPost.classList.add('post');

    const postId = post.id;
    newPost.id = `post-${postId}`;

    newPost.innerHTML = `
        <div class="preview" id="post-preview-${postId}">
            <div class="post flexbox">
                <div class="text-content">
                    <div class="new-post-badge">
                        new
                    </div>
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
                    ${post.display_name ? `<p class="post-author">by ${post.display_name}</p>` : `<p class="post-author">by Anonymous ${post.anon_uuid}</p>`}
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
                                <source src="${post.media_file.url}" type="video/mp4">
                            </video>` : ''}
                        ${post.media_file && post.is_image ? `<img src="${post.media_file.url}" alt="${post.title}" loading="lazy">` : ''}
                        ${post.image ? `<img src="${post.image.url}" alt="${post.title}" loading="lazy">` : ''}
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
                <div id="comment-form-container-${postId}">
                </div>
            </div>
        </div>
    `;
    postList.prepend(newPost); // Add the new post to the top of the list

    loadCommentForm(postId);

    newPost.classList.add("highlight");
    setTimeout(() => newPost.classList.remove("highlight"), 3000); // Remove after 3 seconds


    attachEventListeners();
    attachCopyLinks();
    return newPost;
}

function addCommentToPage(comment) {
    const postList = document.getElementById('post-list');

    const newComment = document.createElement('div');
    newComment.classList.add('item');
    newComment.classList.add('comment');

    const commentId = comment.id;
    newComment.id = `comment-${commentId}`;

    comment.name = comment.name || "Anonymous";

    newComment.innerHTML = `
        <h2 class="${comment.title}">
            Re: 
            <a href="/post/${comment.post_id}">
                ${comment.post_title}
            </a>
        </h2>
        <div class="post-content">
            <strong>${comment.name}</strong>: ${comment.content}
        </div>
        <div class="menu">
            <p><em>${comment.created_on}</em></p>

            <a href="javascript:void(0);" id="toggle-reply-{{post.id}}" class="toggle-reply">Reply</a>
        </div>
        <div id="reply-form-${comment.id}" class="reply-form" style="display: none;">
        </div>
    `;
    postList.prepend(newComment); // Add the new post to the top of the list

    newComment.classList.add("highlight");
    setTimeout(() => newPost.classList.remove("highlight"), 3000); // Remove after 3 seconds

    // Add comment to the comments list if it exists
    const commentsListDiv = document.querySelector(`#comments-list-${comment.post_id}`);
    if (commentsListDiv) {
        const commentElement = document.createElement('div');
        commentElement.className = 'comment';
        commentElement.innerHTML = `
            <strong>${comment.name}</strong>: ${comment.content}
            <p><em>${comment.created_on}</em></p>
        `;
        commentsListDiv.appendChild(commentElement);

        // Update comment count in toggle button
        const toggleButton = document.querySelector(`#toggle-comments-${comment.post_id}`);
        if (toggleButton) {
            const currentCount = parseInt(toggleButton.textContent.match(/\d+/)[0]);
            toggleButton.textContent = `Comments (${currentCount + 1})`;
        }
    }

    attachEventListeners();
    return newPost;
}

function loadCommentForm(postId) {
    const apiUrl = `/api/get-comment-form-html/${postId}/`;

    fetch(apiUrl, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
    })
        .then(response => response.json())
        .then(data => {
            console.log("Response data:", data); // Log the response
            if (data.error) {
                console.error(`Error loading form: ${data.error}`);
                return;
            }

            // Inject the form HTML into the target container
            const formContainer = document.getElementById(`comment-form-container-${postId}`);
            if (formContainer) {
                formContainer.innerHTML = data.form;

                // Update the form action dynamically
                const formElement = formContainer.querySelector('form');
                if (formElement) {
                    formElement.setAttribute('action', data.action_url);

                    // Add an event listener to handle submission
                    formElement.addEventListener('submit', function (e) {
                        e.preventDefault();
                        submitCommentForm(formElement, postId);
                    });
                }
            } else {
                console.error(`Comment form container for post ${postId} not found.`);
            }
        })
        .catch(error => console.error('Error fetching the comment form:', error));
}

function submitCommentForm(formElement, postId) {

    const formData = new FormData(formElement); // Create a FormData object for the form

    fetch(formElement.action, {
        method: "POST",
        body: formData,
        headers: {
            "X-CSRFToken": getCookie('csrftoken'), // Include CSRF token for Django
            'X-Requested-With': 'XMLHttpRequest', 
        },
    })
        .then(response => response.json())
        .then(data => {
            console.log(data);
            if (data.success) {
                console.log("Comment submitted:", data.comment);

                // Optionally add the comment to the page
                addCommentToPage(data.comment);

                // Reset the form
                form.reset();
            } else {
                console.error("Error submitting comment:", data.errors);
                displayFormErrors(form, data.errors); // Display validation errors
            }
        })
        .catch(error => {
            console.error("Error:", error);
        });
}


// Attach to window object to make it globally accessible
window.refreshCSRFToken = refreshCSRFToken;
window.attachCopyLinks = attachCopyLinks;
window.attachEventListeners = attachEventListeners;
window.scrollToElementById = scrollToElementById;
window.showModalIfNeeded = showModalIfNeeded;
window.attachToggleReplyButtons = attachToggleReplyButtons;


