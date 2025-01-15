import { getCookie, refreshCSRFToken } from './load_document_functions.js';

export async function logToBackend(message, level = 'info') {
    console.log(`[${level}] ${message}`);
    
    let csrfToken = getCookie('csrftoken');
    
    // If no CSRF token, try to refresh it
    if (!csrfToken) {
        try {
            csrfToken = await refreshCSRFToken();
        } catch (error) {
            console.warn('Could not obtain CSRF token, skipping backend logging');
            return;
        }
    }
    
    try {
        const response = await fetch(`/api/log-js/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            body: `message=${encodeURIComponent(message)}&level=${level}`,
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
    } catch (error) {
        console.warn('Backend logging failed:', error);
    }
}