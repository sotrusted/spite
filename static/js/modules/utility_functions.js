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

function toggleDetailImage(postId) {
    const imageThumbnail = document.getElementById(`image-thumbnail-${postId}`);
    const imageContainer = document.getElementById(`image-container-${postId}`);
    if (imageThumbnail && imageContainer) {
        if (imageThumbnail.style.display === 'block') {
            imageThumbnail.style.display = 'none';
            imageContainer.style.display = 'block';
        } else {
            imageThumbnail.style.display = 'block';
            imageContainer.style.display = 'none';
        }
    } else {
        log(`Image thumbnail or image container not found for post ${postId}`, 'error');
    }
}


function attachDetailToggleImages(id=null) {
    let detailToggleImages;
    if (id) {
        detailToggleImages = document.querySelectorAll(`a[id^="detail-toggle-image-${id}"]`);
    } else {
        detailToggleImages = document.querySelectorAll('.detail-toggle-image');
    }

    detailToggleImages.forEach(detailToggleImage => {
        if (!detailToggleImage) {
            log('Detail toggle image not found', 'error');
            return;
        }
        if (!detailToggleImage.hasAttribute('data-listener-attached')) {
            detailToggleImage.setAttribute('data-listener-attached', 'true');
            const postId = detailToggleImage.getAttribute('data-post-id')
            detailToggleImage.addEventListener('click', function() {
                toggleDetailImage(postId);
            });
        }
    });

    const detailImageContainers = document.querySelectorAll('.detail-image-container');
    detailImageContainers.forEach(detailImageContainer => {
        detailImageContainer.addEventListener('click', function() {
            const postId = detailImageContainer.getAttribute('data-post-id')
            toggleDetailImage(postId);
        });
    });

    const detailThumbnails = document.querySelectorAll('.detail-thumbnail');
    detailThumbnails.forEach(detailThumbnail => {
        detailThumbnail.addEventListener('click', function() {
            const postId = detailThumbnail.getAttribute('data-post-id')
            toggleDetailImage(postId);
        });
    });
}


function attachToggleContentButtons(id=null) {
    log("Attaching toggle content buttons");
    let toggleContentButtons;
    if (id) {
        toggleContentButtons = document.querySelectorAll(`a[id^="toggle-link-${id}"]`);   
    } else {
        toggleContentButtons = document.querySelectorAll('a[id^="toggle-link-"]');
    }

    log(`Found ${toggleContentButtons.length} toggle content buttons`);
    
    toggleContentButtons.forEach(a => {
        // Only attach listener if not already attached
        if (!a.hasAttribute('data-listener-attached')) {
            a.setAttribute('data-listener-attached', 'true');
            a.addEventListener('click', function() {
                const postId = a.id.replace('toggle-link-', '');
                toggleContent(postId);
            });
            log(`Attached listener to toggle button for post ${a.id}`);
        }
    });

    const previewToggleImages = document.querySelectorAll('.preview-image-container');
    previewToggleImages.forEach(previewToggleImage => {
        if (!previewToggleImage.hasAttribute('data-listener-attached')) {
            previewToggleImage.setAttribute('data-listener-attached', 'true');
            previewToggleImage.addEventListener('click', function() {
                const postId = previewToggleImage.getAttribute('data-post-id');
                toggleContent(postId);
                toggleDetailImage(postId);

            });
        }
    });
}


export function attachToggleReplyButtons(id=null) {
    log("Attaching toggle reply buttons");
    let toggleReplyButtons;
    if (id) {
        toggleReplyButtons = document.querySelectorAll(`a[id^="toggle-reply-${id}"]`);
    } else {
        toggleReplyButtons = document.querySelectorAll('a[id^="toggle-reply-"]');
    }
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
                const replyForm = document.getElementById(`reply-form-${commentId}`);
                
                if (replyForm) {
                    // Toggle the form visibility
                    if (replyForm.style.display === 'none' || replyForm.style.display === '') {
                        replyForm.style.display = 'block';
                        
                        // Add loading indicator if it doesn't exist
                        if (!document.getElementById(`reply-indicator-${commentId}`)) {
                            const indicator = document.createElement('div');
                            indicator.id = `reply-indicator-${commentId}`;
                            indicator.className = 'htmx-indicator';
                            indicator.innerHTML = `
                                <div class="spinner-border spinner-border-sm text-secondary" role="status">
                                    <span class="visually-hidden">Loading reply form...</span>
                                </div>
                                <span class="ms-2">Loading...</span>
                            `;
                            replyForm.appendChild(indicator);
                            
                            // Update the HTMX attributes to use the indicator
                            a.setAttribute('hx-indicator', `#reply-indicator-${commentId}`);
                        }
                        
                        // Add a close button after the form is loaded
                        document.addEventListener('htmx:afterSwap', function(event) {
                            if (event.detail.target.id === `reply-form-${commentId}`) {
                                const formContainer = document.getElementById(`comment-form-container-${commentId}`);
                                if (formContainer) {
                                    formContainer.style.display = 'block';
                                    
                                    // Add close button if it doesn't exist
                                    if (!document.getElementById(`close-reply-${commentId}`)) {
                                        const closeButton = document.createElement('button');
                                        closeButton.id = `close-reply-${commentId}`;
                                        closeButton.className = 'close-reply-btn';
                                        closeButton.innerHTML = '×';
                                        closeButton.onclick = function(e) {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            replyForm.style.display = 'none';
                                        };
                                        
                                        // Insert at the beginning of the form container
                                        if (formContainer.firstChild) {
                                            formContainer.insertBefore(closeButton, formContainer.firstChild);
                                        } else {
                                            formContainer.appendChild(closeButton);
                                        }
                                    }
                                }
                            }
                        }, { once: true });
                    } else {
                        replyForm.style.display = 'none';
                    }
                } else {
                    log(`Reply form for comment ${commentId} not found`, 'error');
                }
            });
        }
    });
    
    log(`Toggle reply buttons attached`);
}


// Function to attach event listeners to copy links
function attachCopyLinks(id=null) {
    log("Attaching copy links");
    let copyLinks;
    if (id) {
        copyLinks = document.querySelectorAll(`a[id^="copy-link-${id}"]`);
    } else {
        copyLinks = document.querySelectorAll('a[id^="copy-link-"]');
    }

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

function attachToggleCommentsButtons(id=null) {
    log('Attaching toggle comments buttons');
    // Update the selector to match your actual button structure
    let toggleCommentsButtons;
    if (id) {
        toggleCommentsButtons = document.querySelectorAll(`button[id^="toggle-comments-${id}"]`);
    } else {
        toggleCommentsButtons = document.querySelectorAll('button[id^="toggle-comments-"]');
    }
 
    if (toggleCommentsButtons.length === 0) {
        log('No toggle comments buttons found', 'warning');
        return;
    }

    toggleCommentsButtons.forEach(button => {
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

                const commentSection = document.getElementById(`comment-section-${postId}`);
                if (!commentSection) {
                    console.error(`Comment section for post ${postId} not found`);
                    return;
                }


                if (!commentSection.querySelector('.comments-container')) {
                    console.log(`Loading comments container for post ${postId}`);
                    htmx.process(commentSection);
                    htmx.trigger(commentSection, 'revealed');

                    // Add a loading indicator
                    commentSection.innerHTML = `
                        <div class="comments-loading">
                            <div class="spinner-border spinner-border-sm text-secondary" role="status">
                                <span class="visually-hidden">Loading comments...</span>
                            </div>
                            <span>Loading comments...</span>
                        </div>
                    `;

                } else {
                    const commentsContainer = commentSection.querySelector('.comments-container');
                    commentsContainer.style.display = 
                        commentsContainer.style.display === 'none' ? 'block' : 'none';
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
export function attachEventListeners(id=null) {
    log('Attaching event listeners');

    if (!id) {
        setWriteLinksScrollers();
        log('Write links scrollers attached');

        attachToggleContentButtons();
        log('Toggle content buttons attached');

        attachCopyLinks();
        log('Copy links attached');

        attachToggleCommentsButtons();
        log('Toggle comments buttons attached');

        attachDetailToggleImages();
        log('Detail toggle images attached');

        attachToggleReplyButtons();
        log('Toggle reply buttons attached');
    }

    if (id) {
        attachToggleContentButtons(id);
        log('Toggle content buttons attached for post ${id}');

        attachCopyLinks(id);
        log('Copy links attached for post ${id}');

        attachToggleCommentsButtons(id);
        log('Toggle comments buttons attached for post ${id}');

        attachDetailToggleImages(id);
        log('Detail toggle images attached for post ${id}');

    }

    // handleCommentFormSubmit();
    // log('Comment form submit listener attached');

    // handleReplyFormSubmit();
    // log('Reply form submit listener attached');

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
        const newPostElement = document.getElementById(`post-${message.id}`) || document.getElementById(`post-skeleton-${message.id}`);
        if (newPostElement) {
            scrollToElementById(newPostElement.id);
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

function createPostElement(post) {
    const newPost = document.createElement('div');
    newPost.classList.add('item');
    newPost.classList.add('post');
    newPost.id = `post-skeleton-${post.id}`;
    
    // The key change is here - make the div itself have the HTMX attributes
    // instead of a paragraph inside it
    newPost.setAttribute('hx-get', `/hx/get-post/${post.id}/`);
    newPost.setAttribute('hx-trigger', 'revealed');
    newPost.setAttribute('hx-swap', 'outerHTML'); // Use outerHTML to replace the entire element
    
    newPost.innerHTML = `
        <p class="post-skeleton">
            Loading post #${post.id}...
            <span id="post-indicator-${post.id}" class="htmx-indicator">
                <div class="spinner-border spinner-border-sm text-secondary" role="status">
                    <span class="visually-hidden"></span>
                </div>
            </span>
        </p>`;
    
    return newPost;
}

export function addPostToPage(post) {
    if (!post || !post.id) {
        console.error('Invalid post data:', post);
        return null;
    }

    const postId = post.id;
    const postList = document.getElementById('post-list');

    // Check if post already exists
    if (document.getElementById(`post-${postId}`)) {
        console.log(`Post ${post.id} already exists in DOM`);
        return null;
    }

    const newPost = createPostElement(post);
    console.log("New post created:", newPost);

    postList.prepend(newPost); // Add the new post to the top of the list


    // Create a promise that resolves when the post is fully loaded
    const postLoadedPromise = new Promise((resolve) => {
        // Set up a mutation observer to watch for when HTMX replaces the skeleton
        const observer = new MutationObserver((mutations, obs) => {
            // Look for the actual post element
            const loadedPost = document.getElementById(`post-${postId}`);
            if (loadedPost) {
                // Post has been loaded, stop observing
                obs.disconnect();
                resolve(loadedPost);
            }
        });
        
        // Start observing the post list for changes
        observer.observe(postList, { 
            childList: true,
            subtree: true 
        });
        
        // Set a timeout to resolve anyway after 5 seconds
        setTimeout(() => {
            observer.disconnect();
            resolve(document.getElementById(`post-${postId}`));
        }, 5000);
    });

    // Process with HTMX
    htmx.process(newPost);
    htmx.trigger(newPost, 'revealed');

    // Wait for the post to be fully loaded before attaching event handlers
    postLoadedPromise.then((loadedPost) => {
        if (!loadedPost) {
            console.warn(`Post ${postId} was not properly loaded`);
            return;
        }
        
        // Add highlight effect
        loadedPost.classList.add("highlight");
        setTimeout(() => loadedPost.classList.remove("highlight"), 3000);

        // Attach all event listeners
        attachToggleContentButtons(postId);
        log('Toggle content buttons attached');

        attachCopyLinks(postId);
        log('Copy links attached');

        attachToggleCommentsButtons(postId);
        log('Toggle comments buttons attached');

        attachToggleReplyButtons(postId);
        log('Toggle reply buttons attached');
    });
    
    return newPost;
}

function createCommentElement(comment, isInline = false) {
    const element = document.createElement('div');
    element.classList.add('comment');

    if (isInline) {
        element.id = `comment-${comment.id}-inline`;
        // Match detail.html inline comment format
        element.innerHTML = `
            <strong>${comment.name || 'Anonymous'}</strong>
            ${comment.content}
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
        element.id = `comment-${comment.id}`;

        element.innerHTML = `
            <p class="comment-skeleton"
                 hx-get="/hx/get-comment/${comment.id}/"
                 hx-trigger="revealed"
                 hx-target="#comment-${comment.id}"
                 hx-swap="innerHTML"
                hx-indicator="#comment-indicator-${comment.id}">
                Loading comment #${comment.id}...
                <span id="comment-indicator-${comment.id}" class="htmx-indicator">
                    <div class="spinner-border spinner-border-sm text-secondary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </span>
            </p>
        `
    }

    return element;
}

export function addCommentToPage(comment) {
    const postList = document.getElementById('post-list');
    const newComment = createCommentElement(comment);
    postList.insertBefore(newComment, postList.firstChild);

    // Add to comment list if it exists
    const commentList = document.getElementById(`comments-list-${comment.post_id}`);
    if (commentList) {
        const inlineComment = createCommentElement(comment, true);
        commentList.appendChild(inlineComment);

        // Update comment count if button exists
        const commentButton = document.getElementById(`toggle-comments-${comment.post_id}`);
        if (commentButton) {
            const commentCountElement = commentButton.querySelector('.comment-count');
            const currentCount = parseInt(commentCountElement.querySelector('.comment-count').textContent.match(/\d+/)[0]);
            commentCountElement.textContent = `(${currentCount + 1})`;
        }
    }


    const htmxProcessingPromise = new Promise ((resolve => {
        // Process the new comment
        htmx.process(newComment);

        // Use MutationObserver to wait for the comment to be fully loaded
        const observer = new MutationObserver((mutations, obs) => {
            const loadedComment = document.getElementById(`comment-${comment.id}`);
            if (loadedComment) {
                obs.disconnect();
                resolve(loadedComment);
            }
        });

        observer.observe(newComment, {
            childList: true, 
            subtree: true, 
            attributes: true, 
            attributeFilter: ['hx-get', 'class'] 
        });
        
        // Set a timeout to resolve anyway after 5 seconds
        setTimeout(() => {
            observer.disconnect();
            resolve(document.getElementById(`comment-${comment.id}`));  
        }, 5000);

        //Trigger the revealed event`   
        htmx.trigger(newComment, 'revealed');
    }));

    // Wait for the comment to be fully loaded before attaching event handlers
    htmxProcessingPromise.then(loadedComment => {
        if (!loadedComment) {
            console.warn(`Comment ${comment.id} was not properly loaded`);
            return;
        }

        attachEventListeners(comment.id, 'comment');
    });

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
                        console.log("Form submitted");
                        /*
                        e.preventDefault();
                        submitCommentForm(formElement, postId);
                        */
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
                console.log("Form element found");
                /*
                formElement.setAttribute('action', data.action_url);
                formElement.addEventListener('submit', function(e) {
                    e.preventDefault();
                    submitCommentForm(formElement, postId);
                });
                */
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

    const progress = form.querySelector(`.upload-progress-${postId}`);
    
    if (progress) {
        progress.style.display = 'block';
    }


    const formData = new FormData(formElement); // Create a FormData object for the form

    fetch(formElement.action, {
        method: "POST",
        body: formData,
        headers: {
            "X-CSRFToken": getCookie('csrftoken'), // Include CSRF token for Django
            'X-Requested-With': 'XMLHttpRequest', 
        },
        timeout: 60000,
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
        alert('Error uploading comment. Please try again.');
        displayFormErrors(formElement, data.errors);
        logToBackend(`Error submitting comment: ${error.message}`, 'error');
    })
    .finally(() => {
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.value = 'Submit';
            progress.style.display = 'none';

        }
    });
}

// Process HTMX triggers on dynamically added elements
export function processHtmxOnNewElements() {
    // Find all elements with hx-trigger="revealed" that haven't been processed
    const unprocessedElements = document.querySelectorAll('[hx-trigger="revealed"]:not([data-processed="true"])');
    
    unprocessedElements.forEach(element => {
        // Mark as processed to avoid reprocessing
        element.setAttribute('data-processed', 'true');
        
        // Process HTMX on this element
        htmx.process(element);
        
        // Force the revealed event if the element is in the viewport
        if (isElementInViewport(element)) {
            htmx.trigger(element, 'revealed');
        }
    });
}

// Check if an element is in the viewport
function isElementInViewport(el) {
    const rect = el.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

// Call this periodically to process new elements
export function setupHtmxProcessing() {
    // Process immediately
    processHtmxOnNewElements();
    
    // Then set up an interval to check for new elements
    setInterval(processHtmxOnNewElements, 1000);
    
    // Also process on scroll events
    window.addEventListener('scroll', function() {
        processHtmxOnNewElements();
    });
}

window.scrollToElementById = scrollToElementById;

function toggleReplyForm(commentId) {
    const replyForm = document.getElementById(`reply-form-${commentId}`);
    
    // Show the form when clicked
    replyForm.style.display = 'block';
    
    // Add a close button to the form after it's loaded
    setTimeout(() => {
        if (!document.getElementById(`close-reply-${commentId}`)) {
            const closeButton = document.createElement('button');
            closeButton.id = `close-reply-${commentId}`;
            closeButton.className = 'close-reply-btn';
            closeButton.innerHTML = '×';
            closeButton.onclick = function() {
                replyForm.style.display = 'none';
            };
            
            // Insert at the beginning of the form
            if (replyForm.firstChild) {
                replyForm.insertBefore(closeButton, replyForm.firstChild);
            } else {
                replyForm.appendChild(closeButton);
            }
        }
    }, 500); // Short delay to ensure content is loaded
}

window.toggleReplyForm = toggleReplyForm;


/**
 * Cleans up comment skeletons that have already been loaded
 * This prevents duplicate content and improves page performance
 */
export function cleanupCommentSkeletons() {
    log("Cleaning up comment skeletons");
    
    // Find all comment skeletons
    const skeletons = document.querySelectorAll('.comment-skeleton');
    
    if (skeletons.length === 0) {
        log("No comment skeletons found to clean up");
        return;
    }
    
    log(`Found ${skeletons.length} comment skeletons to check`);
    let removedCount = 0;
    
    skeletons.forEach(skeleton => {
        // Get the parent element which should have id="comment-{id}"
        const parentElement = skeleton.closest('[id^="comment-"]');
        if (!parentElement) return;
        
        // Extract the comment ID from the parent element's ID
        const parentId = parentElement.id;
        const match = parentId.match(/comment-(\d+)/);
        if (!match || !match[1]) return;
        
        const commentId = match[1];
        
        // Find all elements with this comment ID
        const commentElements = document.querySelectorAll(`#comment-${commentId}`);
        
        // If we have more than one element with this ID, then the comment has been loaded
        if (commentElements.length > 1) {
            skeleton.remove();
            removedCount++;
            log(`Removed skeleton for comment #${commentId} (duplicate ID found)`);
        } else {
            // Check if the parent element has content other than the skeleton
            // Count children that aren't the skeleton or loading indicators
            const contentElements = Array.from(parentElement.children).filter(child => {
                return !child.classList.contains('comment-skeleton') && 
                       !child.classList.contains('htmx-indicator');
            });
            
            if (contentElements.length > 0) {
                skeleton.remove();
                removedCount++;
                log(`Removed skeleton for comment #${commentId} (content loaded)`);
            }
        }
    });
    
    log(`Cleaned up ${removedCount} comment skeletons`);
}

// Add this to your initialization code or document ready function
export function initSkeletonCleanup() {
    // Run immediately
    cleanupCommentSkeletons();
    
    // Then run periodically
    setInterval(cleanupCommentSkeletons, 3000); // Check every 3 seconds
    
    // Also run after HTMX swaps
    document.addEventListener('htmx:afterSwap', function(event) {
        // Small delay to ensure DOM is updated
        setTimeout(cleanupCommentSkeletons, 500);
    });
}