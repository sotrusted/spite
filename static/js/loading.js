import { logToBackend, refreshCSRFToken } from "./modules/load_document_functions.js";

async function initialize() {
    refreshCSRFToken();

    console.log("Loading screen initialized");
    logToBackend("Loading screen initialized", 'info');

}

// Set cookie and log it
document.cookie = "loading_complete=true; path=/";
console.log("Set loading_complete cookie");
logToBackend("Set loading_complete cookie", 'info');
console.log("Current cookies:", document.cookie);
logToBackend("Current cookies: " + document.cookie, 'info');
// Redirect with logging
setTimeout(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const targetUrl = urlParams.get('to');
    
    logToBackend(`URL Params - to: ${targetUrl}`, 'info');

    if (targetUrl) {
        console.log("Redirecting to:", targetUrl);
        logToBackend(`Redirecting to: ${targetUrl}`, 'info');
        window.location.href = targetUrl;
    }
}, 100);
