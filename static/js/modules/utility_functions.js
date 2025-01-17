import { logToBackend, getCookie, setCookie, scrollToElementById } from './load_document_functions.js';

function log(message, level = 'info') {
    logToBackend(message, level);
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

function attachToggleContentButtons() {
    log("Attaching toggle content buttons");
    const toggleContentButtons = document.querySelectorAll('a[id^="toggle-link-"]');
    log(`Found ${toggleContentButtons.length} toggle content buttons`);
    toggleContentButtons.forEach(a => {
        a.addEventListener('click', function() {
            toggleContent(a.id.replace('toggle-link-', ''));
        });
    });
}

function attachToggleReplyButtons() {
    log("Attaching toggle reply buttons");
    const toggleReplyButtons = document.querySelectorAll('a[id^="toggle-reply-"]');
    log(`Found ${toggleReplyButtons.length} toggle reply buttons`);

    if (toggleReplyButtons.length === 0) {
        log("No toggle reply buttons found", 'warning');
        return;
    }

    toggleReplyButtons.forEach(a => {
        if (!a.hasAttribute('data-listener-attached')) {
            a.setAttribute('data-listener-attached', 'true');
            const commentId = a.id.split('-').pop();
            log(`Attaching click listener to reply button for comment ${commentId}`);
            
            a.addEventListener('click', function() {
                log(`Reply button clicked for comment ${commentId}`);
                const commentReplyForm = document.querySelector(`div[id^=reply-form-${commentId}]`);
                
                if (commentReplyForm) {
                    const isHidden = commentReplyForm.style.display === 'none';
                    commentReplyForm.style.display = isHidden ? 'block' : 'none';
                    log(`Reply form for comment ${commentId} ${isHidden ? 'shown' : 'hidden'}`);
                } else {
                    log(`Reply form for comment ${commentId} not found`, 'error');
                }
            });
        }
    });
}


// Function to attach event listeners to copy links
function attachCopyLinks() {
    log("Attaching copy links");
    const copyLinks = document.querySelectorAll('a[id^="copy-link-"]');
    log(`Found ${copyLinks.length} copy links`);
    if (copyLinks.length === 0) {
        log("No copy links found", 'warning');
        return;
    }
    copyLinks.forEach(a => {
        if (!a.hasAttribute('data-listener-attached')) {
            a.setAttribute('data-listener-attached', 'true');
            log(`Attaching click listener to copy link ${a.id}`);
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
                })
                .catch(err => {
                    console.error('Failed to copy link:', err);
                    alert('Failed to copy the link. Please try again.');
                });
            });
        }
    });
}

function attachToggleCommentsButtons() {
    log('Attaching toggle comments buttons');
    const buttons = document.querySelectorAll('[id^="toggle-comments-"]');
    
    if (buttons.length === 0) {
        log('No toggle comments buttons found', 'warning');
        return;
    }

    buttons.forEach(button => {
        if (!button.hasAttribute('data-listener-attached')) {
            button.setAttribute('data-listener-attached', 'true');
            
            // Extract post ID from button ID instead of data attribute
            const postId = button.id.replace('toggle-comments-', '');
            
            log(`Attaching click listener to comments button for post ${postId}`);
            
            button.addEventListener('click', function() {
                if (!postId) {
                    log('No post ID found for comments button', 'error');
                    return;
                }
                
                log(`Comments button clicked for post ${postId}`);
                
                const commentsContainer = document.getElementById(`comments-container-${postId}`);
                if (commentsContainer) {
                    const isHidden = commentsContainer.style.display === 'none';
                    commentsContainer.style.display = isHidden ? 'block' : 'none';
                    log(`Comments container for post ${postId} ${isHidden ? 'shown' : 'hidden'}`);
                } else {
                    log(`Comments container for post ${postId} not found`, 'error');
                }
            });
        } else {
            log(`Listener already attached to comments button for post ${button.getAttribute('data-post-id')}`);
        }
    });
}

// Handle regular comment forms
function handleCommentFormSubmit(form) {
    const commentForms = document.querySelectorAll('form[id^="comment-form-"]');
    log(`Found ${commentForms.length} comment forms`);

    commentForms.forEach(form => {
        if (!form.hasAttribute('data-listener-attached')) {
            form.setAttribute('data-listener-attached', 'true');
            log(`Attaching submit listener to comment form ${form.id}`);
            const formId = form.id.replace('comment-form-', '');
            log(`Form ID: ${formId}`);

            form.addEventListener('submit', function (e) {
                e.preventDefault();
                log(`Comment form ${formId} submitted`);
                const formData = new FormData(this);
                const url = this.action;

                fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: formData,
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.reset();
                        console.log("Comment submitted successfully");
                    }
                })
                .catch(error => console.error("Error:", error));
            });
        }
    });
}

function handleReplyFormSubmit() {
    // Handle reply forms
    const replyForms =  document.querySelectorAll('form[id^="reply-form-"]');
    log(`Found ${replyForms.length} reply forms`);

    replyForms.forEach(form => {
        if (!form.hasAttribute('data-listener-attached')) {
            form.setAttribute('data-listener-attached', 'true');
            const formId = form.id;
            log(`Attaching submit listener to ${formId}`);

            form.addEventListener('submit', function (e) {
                e.preventDefault();
                log(`Reply form ${formId} submitted`);
                const formData = new FormData(this);
                const url = this.action;

                fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: formData,
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.reset();
                        this.closest('.reply-form').style.display = 'none';
                        console.log("Reply submitted successfully");
                    }
                })
                .catch(error => console.error("Error:", error));
            });
        }
    });
}


// Attach submit event to all comment forms
export function attachEventListeners() {
    log('Attaching event listeners');

    setWriteLinksScrollers();
    log('Write links scrollers attached');

    attachToggleContentButtons();
    log('Toggle content buttons attached');

    attachCopyLinks();
    log('Copy links attached');

    attachToggleCommentsButtons();
    log('Toggle comments buttons attached');

    attachToggleReplyButtons();
    log('Toggle reply buttons attached');


    handleCommentFormSubmit();
    log('Comment form submit listener attached');

    handleReplyFormSubmit();
    log('Reply form submit listener attached');

    document.querySelectorAll('#feed-scroller').forEach(a => {
        a.addEventListener('click', () => scrollToElementById('recent-posts'));
    });
    log('Feed scroller attached');
}



export function disableSubmitButton(form) {
    var submitButton = document.getElementById('submit-id-submit');
    console.log(submitButton.value);
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';
    }
}


export function enableSubmitButton(form) {
    var submitButton = document.getElementById('submit-id-submit');
    submitButton.disabled = false;
    submitButton.value = 'Post';  // Change the button text
}


export function updateSpiteCounter() {
    const counterElement = document.getElementById("spite-counter");
    const currentCount = parseInt(counterElement.textContent.split(":")[1].trim());
    counterElement.textContent = `SPITE COUNTER: ${currentCount + 1}`;
}


// Function to show the notification
export function showNewPostNotification(message) {
    const notificationButton = document.getElementById("new-post-notification");
    const notificationTitle = document.getElementById("new-post-title");
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
export function showNewCommentNotification(message) {
    const commentNotificationButton = document.getElementById("new-comment-notification");
    const commentNotificationTitle = document.getElementById("new-comment-post"); 

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


function setWriteLinksScrollers() {
    document.querySelectorAll('.post-link').forEach(a => {
        a.addEventListener('click', function () {
            scrollToElementById('post-form');
        });
    });
}


export function addPostToPage(post) {
    const postId = post.id;
    const postList = document.getElementById('post-list');

    // Check if post already exists
    if (document.getElementById(`post-${postId}`)) {
        console.log(`Post ${post.id} already exists in DOM`);
        return null;
    }

    const newPost = document.createElement('div');
    newPost.classList.add('item');
    newPost.classList.add('post');

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
                        <a href="javascript:void(0);" class="toggle-link" id="toggle-link-${postId}">Expand</a>
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

function createCommentElement(comment, isInline = false) {
    const element = document.createElement('div');
    element.classList.add('comment');
    
    if (isInline) {
        element.id = `comment-${comment.id}-inline`;
        // Match detail.html inline comment format
        element.innerHTML = `
            <strong>${comment.name || 'Anonymous'}</strong>: ${comment.content}
            ${comment.media_file || comment.image ? `
                <div class="image-container">
                    ${comment.media_file && comment.is_video ? `
                        <video controls>
                            <source src="${comment.media_file.url}" type="video/mp4">
                        </video>` : ''}
                    ${comment.media_file && comment.is_image ? `
                        <img src="${comment.media_file.url}" alt="Comment image" loading="lazy">` : ''}
                    ${comment.image ? `
                        <img src="${comment.image.url}" alt="Comment image" loading="lazy">` : ''}
                </div>` : ''}
            <p><em>${comment.created_on}</em></p>
        `;
    } else {
        // Match comment.html format for feed view
        element.classList.add('item');
        element.id = `comment-${comment.id}`;
        element.innerHTML = `
            <h2>
                Re: <a href="/post/${comment.post_id}">
                    ${comment.post_title}
                </a>
            </h2>
            <div class="post-content">
                <strong>${comment.name || 'Anonymous'}</strong>: ${comment.content}
                ${comment.media_file || comment.image ? `
                    <div class="image-container">
                        ${comment.media_file && comment.is_video ? `
                            <div class="video-container">
                                <video controls>
                                    <source src="${comment.media_file.url}" type="video/mp4">
                                </video>
                            </div>` : ''}
                        ${comment.media_file && comment.is_image ? `
                            <div class="image-container">
                                <img src="${comment.media_file.url}" alt="Comment image">
                            </div>` : ''}
                        ${comment.image ? `
                            <div class="image-container">
                                <img src="${comment.image.url}" alt="Comment image">
                            </div>` : ''}
                    </div>` : ''}
            </div>
            <div class="menu">
                <p><em>${comment.created_on}</em></p>
                <a href="javascript:void(0);" id="toggle-reply-${comment.id}" class="toggle-reply">Reply</a>
            </div>
            <div id="reply-form-${comment.id}" class="reply-form" style="display: none;">
            </div>
        `;
    }

    return element;
}

export function addCommentToPage(comment) {
    const postList = document.getElementById('post-list');
    const newComment = createCommentElement(comment);
    postList.insertBefore(newComment, postList.firstChild);

    // Load reply form for the new comment
    const replyFormContainer = document.getElementById(`reply-form-${comment.id}`);
    if (replyFormContainer) {
        loadReplyForm(comment.id, comment.post_id);
    }


    // Add to comment list if it exists
    const commentList = document.getElementById(`comments-list-${comment.post_id}`);
    if (commentList) {
        const inlineComment = createCommentElement(comment, true);
        commentList.appendChild(inlineComment);

        // Update comment count if button exists
        const commentButton = document.getElementById(`toggle-comments-${comment.post_id}`);
        if (commentButton) {
            const currentCount = parseInt(commentButton.textContent.match(/\d+/)[0]);
            commentButton.textContent = `Comments (${currentCount + 1})`;
        }
    }

    return newComment;
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

// Add this function to handle loading reply forms
function loadReplyForm(commentId, postId) {
    const apiUrl = `/api/get-reply-form-html/${commentId}/`;
    
    fetch(apiUrl, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error(`Error loading reply form: ${data.error}`);
            return;
        }

        const formContainer = document.getElementById(`reply-form-${commentId}`);
        if (formContainer) {
            formContainer.innerHTML = data.form;
            
            // Add event listener to the new form
            const formElement = formContainer.querySelector('form');
            if (formElement) {
                formElement.setAttribute('action', data.action_url);
                formElement.addEventListener('submit', function(e) {
                    e.preventDefault();
                    submitCommentForm(formElement, postId);
                });
            }
        }
    })
    .catch(error => {
        console.error('Error fetching reply form:', error);
        logToBackend(`Error loading reply form for comment ${commentId}: ${error}`, 'error');
    });
}

function submitCommentForm(formElement, postId) {
    // Prevent double submission
    const submitButton = formElement.querySelector('button[type="submit"]');
    if (submitButton?.disabled) return;
    
    // Disable submit button
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.value = 'Submitting...';
    }


    const formData = new FormData(formElement); // Create a FormData object for the form

    fetch(formElement.action, {
        method: "POST",
        body: formData,
        headers: {
            "X-CSRFToken": getCookie('csrftoken'), // Include CSRF token for Django
            'X-Requested-With': 'XMLHttpRequest', 
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        logToBackend(`Comment submitted successfully`, 'info');
        if (data.success) {
            formElement.reset();
            
            // Don't add comment here - let the websocket handle it
            // This prevents duplicate comments
            console.log("Comment submitted successfully");
        } else {
            console.error("Error submitting comment:", data.errors);
            displayFormErrors(formElement, data.errors);
        }
    })
    .catch(error => {
        console.error("Error submitting comment:", error);
        logToBackend(`Error submitting comment: ${error.message}`, 'error');
    })
    .finally(() => {
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.value = 'Submit';
        }
    });
}