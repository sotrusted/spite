import { logToBackend, refreshCSRFToken, showModalIfNeeded, scrollToElementById } from './modules/load_document_functions.js';
import { attachEventListeners, processHtmxOnNewElements, setupHtmxProcessing } from './modules/utility_functions.js';
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

    
});
