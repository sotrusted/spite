/**
 * HTMX Infinite Scroll - Fallback for non-HTMX browsers
 * HTMX handles infinite scroll natively with hx-trigger="intersect once"
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if HTMX is available
    if (typeof htmx === 'undefined') {
        console.log('HTMX not available, showing fallback pagination');
        const fallback = document.getElementById('fallback-pagination');
        if (fallback) {
            fallback.style.display = 'block';
        }
    } else {
        console.log('HTMX is available - infinite scroll will work natively');
    }
});


