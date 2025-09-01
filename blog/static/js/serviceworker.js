console.log('SERVICEWORKER.JS: Service Worker Initialized');

self.addEventListener('fetch', function(event) {
    console.log('SERVICEWORKER.JS: Fetch event for:', event.request.url);
    
    // Skip cross-origin requests
    if (!event.request.url.startsWith(self.location.origin) && 
        !event.request.url.includes('cdnjs.cloudflare.com')) {
        console.log('SERVICEWORKER.JS: Skipping cross-origin request for:', event.request.url);
        return;
    }

    // Skip API endpoints - let them be handled directly by the server
    if (event.request.url.includes('/api/') || 
        event.request.url.includes('/hx/') ||
        event.request.url.includes('/ws/')) {
        console.log('SERVICEWORKER.JS: Skipping API/HTMX/WebSocket request for:', event.request.url);
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(function(response) {
                // Return cached response if found
                if (response) {
                    console.log('SERVICEWORKER.JS: Returning cached response for:', event.request.url);
                    return response;
                }

                // Clone the request because it's a one-time use stream
                var fetchRequest = event.request.clone();

                return fetch(fetchRequest).then(
                    function(response) {
                        // Check if valid response
                        if(!response || response.status !== 200 || response.type !== 'basic') {
                            console.log('SERVICEWORKER.JS: Non-cacheable response for:', event.request.url);
                            return response;
                        }

                        // Clone the response because it's a one-time use stream
                        var responseToCache = response.clone();

                        caches.open('spite-cache-v1')
                            .then(function(cache) {
                                console.log('SERVICEWORKER.JS: Caching response for:', event.request.url);
                                cache.put(event.request, responseToCache);
                            });

                        return response;
                    }
                ).catch(function(error) {
                    console.error('SERVICEWORKER.JS: Fetch failed for:', event.request.url, error);
                    return new Response('Network request failed', {
                        status: 503,
                        statusText: 'Service Unavailable',
                        headers: new Headers({
                            'Content-Type': 'text/plain'
                        })
                    });
                });
            })
    );
}); 