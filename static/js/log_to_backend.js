function logToBackend(message, level = 'info') {
    const baseUrl = window.location.origin;
    console.log(`Base URL: ${baseUrl}`);
    fetch(`${baseUrl}/log-js/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: `message=${encodeURIComponent(message)}&level=${level}`
    })
    .catch(error => {
        console.error('Error logging to backend:', error);
        // Fallback to console logging if backend fails
        console.log(`[${level}] ${message}`);
    });
}
window.logToBackend = logToBackend;