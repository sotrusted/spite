import { logToBackend, refreshCSRFToken, showModalIfNeeded, scrollToElementById } from './modules/load_document_functions.js';
import { attachEventListeners, processHtmxOnNewElements, setupHtmxProcessing, initSkeletonCleanup, toggleContent, reattachEventListenersForInitialPosts, attachEventListenersToNewPosts } from './modules/utility_functions.js';
// import { initAjaxPostForm } from './ajax_posts.js';
import { initPostWebsocketUpdates, initCommentWebsocketUpdates, initChatWebsocketUpdates, initSiteNotifications } from './websocket_updates.js';

logToBackend("Base.js initialized", 'info');
console.log("Base.js initialized");

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOMContentLoaded");

    refreshCSRFToken();
    logToBackend("CSRF token refreshed", 'info');

    showModalIfNeeded();
    logToBackend("Modal shown if needed", 'info');

    // Add a small delay to ensure DOM is fully rendered
    setTimeout(() => {
        attachEventListeners();
        logToBackend("Event listeners attached", 'info');
        
        // Double-check that initially loaded posts have event listeners
        setTimeout(() => {
            reattachEventListenersForInitialPosts();
        }, 200);
    }, 100);

    // initAjaxPostForm();
    logToBackend("Post form submitted", 'info');

    initPostWebsocketUpdates();
    logToBackend("Post Websocket updates initialized", 'info');

    initCommentWebsocketUpdates();
    logToBackend("Comment Websocket updates initialized", 'info');

    initChatWebsocketUpdates();
    logToBackend("Chat Websocket updates initialized", 'info');

    initSiteNotifications();
    logToBackend("Site notifications initialized", 'info');

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
    
    // Handle infinite scroll posts - attach event listeners when new posts are loaded
    document.addEventListener('htmx:afterSwap', function(event) {
        // Check if this is an infinite scroll request (target is #post-list)
        if (event.detail.target && event.detail.target.id === 'post-list') {
            logToBackend('Infinite scroll content loaded, attaching event listeners', 'info');
            
            // Add a small delay to ensure DOM is updated
            setTimeout(() => {
                attachEventListenersToNewPosts();
            }, 100);
        }
    });

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
    
        // Toggle comments button - handled by utility_functions.js
        // Removed conflicting handler to prevent double event binding
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

        // Toggle link handling is now done by individual event listeners in utility_functions.js
        // Removed to prevent conflicts

        // Debug: log all clicks to see what's happening
        if (target.classList.contains('toggle-link')) {
            console.log('Toggle link clicked (class-based):', target.id, target);
        }

    });
    
});
