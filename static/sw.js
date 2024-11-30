const CACHE_NAME = 'pwa-cache-v1';
const urlsToCache = [
    '/',
    '/static/css/styles.css',
    '/static/js/utility_functions.js',
    '/static/js/ajax_posts.js',
    '/static/js/websocket_updates.js',
    '/static/images/anon.jpg',
    '/static/images/spite-logo.jpg',
];

// Install the service worker
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            console.log('Opened cache');
            return cache.addAll(urlsToCache);
        })
    );
});

// Fetch resources
self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request);
        })
    );
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
