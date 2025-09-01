import { logToBackend, refreshCSRFToken, showModalIfNeeded, scrollToElementById } from './modules/load_document_functions.js';
import { attachEventListeners, processHtmxOnNewElements, setupHtmxProcessing, initSkeletonCleanup } from './modules/utility_functions.js';
// import { initAjaxPostForm } from './ajax_posts.js';
import { initPostWebsocketUpdates, initCommentWebsocketUpdates, initChatWebsocketUpdates } from './websocket_updates.js';

logToBackend("Base.js initialized", 'info');
console.log("Base.js initialized");

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOMContentLoaded");

    refreshCSRFToken();
    logToBackend("CSRF token refreshed", 'info');

    showModalIfNeeded();
    logToBackend("Modal shown if needed", 'info');

    attachEventListeners();
    logToBackend("Event listeners attached", 'info');

    // initAjaxPostForm();
    logToBackend("Post form submitted", 'info');

    initPostWebsocketUpdates();
    logToBackend("Post Websocket updates initialized", 'info');

    initCommentWebsocketUpdates();
    logToBackend("Comment Websocket updates initialized", 'info');

    initChatWebsocketUpdates();
    logToBackend("Chat Websocket updates initialized", 'info');

    scrollToElementById('post-list');

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistrations().then(function(registrations) {
            for(let registration of registrations) {
                registration.unregister();
            }
        });

    }

    setupHtmxProcessing();
    initSkeletonCleanup();

    const writeButton = document.getElementById('write-button');
    if (writeButton) {
        writeButton.addEventListener('click', function() {
            scrollToElementById('post-form');
        });
    }
    const postButton = document.getElementById('post-button');
    if (postButton) {
        postButton.addEventListener('click', function() {
            scrollToElementById('post-form');
        });
    }

    document.getElementById('post-list').addEventListener('click', function(event) {
        const target = event.target;
    
        // Toggle comments button
        if (target.id && target.id.startsWith('toggle-comments-')) {
            const postId = target.id.replace('toggle-comments-', '');

            console.log('Toggle comments clicked for post:', postId);
            
            // Call your existing attachToggleComments function or implement the logic here
            // attachToggleComments(postId);
            
            // Or implement the toggle logic directly:
            const commentSection = document.getElementById(`comment-section-${postId}`);
            const commentsContainer = document.getElementById(`comments-container-${postId}`);
            
            if (commentsContainer.style.display === 'none') {
                commentsContainer.style.display = 'block';
                target.innerHTML = '↩ <span class="comment-count">(0)</span>';
            } else {
                commentsContainer.style.display = 'none';
                target.innerHTML = '↩ <span class="comment-count">(0)</span>';
            }
        }
        // Toggle comment expand/collapse
        if (target.id && target.id.startsWith('expand-comment-')) {
            const commentId = target.id.replace('expand-comment-', '');
            console.log('Toggle comment clicked for comment:', commentId);
            
            const preview = document.getElementById(`comment-preview-${commentId}`);
            const detail = document.getElementById(`comment-detail-${commentId}`);
            
            if (detail.style.display === 'none') {
                preview.style.display = 'none';
                detail.style.display = 'block';
                target.textContent = 'Collapse';
            } else {
                preview.style.display = 'block';
                detail.style.display = 'none';
                target.textContent = 'Expand';
            }
        }

        if (target.id && target.classList.contains('close-reply-btn')) {
            const commentId = target.id.replace('close-reply-btn-', '');
            console.log('Close reply button clicked for comment:', commentId);
            const replyForm = document.getElementById(`reply-form-${commentId}`);
            console.log('Reply form:', replyForm);
            if (replyForm) {
                console.log('Reply form found, hiding it');
                replyForm.style.setProperty('display','none','important');
                replyForm.classList.add('hidden');

            }
        }

    });
    
});
