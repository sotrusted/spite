const CACHE_NAME = 'pwa-cache-v1';

// Separate static assets that rarely change
const STATIC_ASSETS = [
    '/static/images/anon.jpg',
    '/static/images/spite-logo.jpg',
];

// Dynamic assets that need frequent updates
const DYNAMIC_ASSETS = [
    '/static/css/styles.css',
    '/static/js/modules/utility_functions.js',
    '/static/js/ajax_posts.js',
    '/static/js/websocket_updates.js',
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            // Cache files individually to handle failures gracefully
            return Promise.allSettled(
                STATIC_ASSETS.map(url => 
                    cache.add(url).catch(err => {
                        console.error(`Failed to cache ${url}:`, err);
                        // Continue despite the error
                        return Promise.resolve();
                    })
                )
            );
        })
    );
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    
    // For dynamic assets, always go to network first, fall back to cache
    if (DYNAMIC_ASSETS.some(asset => url.pathname.endsWith(asset))) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    // Cache the new version in the background
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseClone);
                    });
                    return response;
                })
                .catch(() => {
                    // If network fails, use cached version
                    return caches.match(event.request);
                })
        );
    } else {
        // For static assets, check cache first, then network
        event.respondWith(
            caches.match(event.request)
                .then(response => response || fetch(event.request))
        );
    }
});

// Update the service worker
self.addEventListener('activate', event => {
    const cacheWhitelist = [CACHE_NAME];
    event.waitUntil(
        caches.keys().then(cacheNames =>
            Promise.all(
                cacheNames.map(cacheName => {
                    if (!cacheWhitelist.includes(cacheName)) {
                        return caches.delete(cacheName);
                    }
                })
            )
        )
    );
});
