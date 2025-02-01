const CACHE_NAME = 'pwa-cache-v2';

// Separate static assets that rarely change
const STATIC_ASSETS = [
    '/static/images/anon.jpg',
    '/static/images/spite-logo.jpg',
    '/static/sounds/harp.mp3'
];

// Dynamic assets that need frequent updates
const DYNAMIC_ASSETS = [
    '/static/css/styles.css',
    '/static/js/modules/utility_functions.js',
    '/static/js/ajax_posts.js',
    '/static/js/websocket_updates.js'
];

// External resources to bypass service worker
const BYPASS_URLS = [
    'fonts.googleapis.com',
    'fonts.gstatic.com',
    'www.googletagmanager.com',
    'www.google-analytics.com',
    'stats.g.doubleclick.net',
    'cdnjs.cloudflare.com'
];

// Dynamic content paths that should always try network first
const DYNAMIC_PATHS = [
    '/api/',
    '/load-more/',
    '/home',
    '/',  // Root path for home page
    '/static/js/',  // All JavaScript files
    '.js',  // Any JavaScript file anywhere
    '/templates/',  // All templates
    '.html'  // Any HTML file
];

console.log('SW.JS: Service Worker Initialized');

self.addEventListener('install', event => {
    console.log('SW.JS: Installing Service Worker');
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            // Cache files individually to handle failures gracefully
            return Promise.allSettled(
                STATIC_ASSETS.map(url => 
                    cache.add(url).catch(err => {
                        console.error(`Failed to cache ${url}:`, err);
                        return Promise.resolve();
                    })
                )
            );
        })
    );
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    
    // Check if this is an external resource we should bypass
    if (BYPASS_URLS.some(domain => url.hostname.includes(domain))) {
        console.log('SW.JS: Bypassing service worker for:', url.hostname);
        return;
    }

    // Only handle GET requests
    if (event.request.method !== 'GET') {
        console.log('SW.JS: Bypassing non-GET request:', event.request.method);
        return;
    }

    console.log('SW.JS: Fetch event for:', event.request.url);
    
    // Check if this is a dynamic content path or JS file
    const isDynamicPath = DYNAMIC_PATHS.some(path => 
        url.pathname.startsWith(path) || url.pathname.endsWith(path)
    );
    
    // For dynamic content, always try network first
    if (isDynamicPath) {
        console.log('SW.JS: Dynamic content request for:', url.pathname);
        event.respondWith(
            fetch(event.request, { cache: 'no-store' })  // Force network request
                .then(response => {
                    if (!response || !response.ok) {
                        throw new Error('Network fetch failed');
                    }
                    console.log('SW.JS: Got fresh response for:', url.pathname);
                    return response;
                })
                .catch(error => {
                    console.log('SW.JS: Network failed for dynamic content, using cache:', url.pathname);
                    return caches.match(event.request);
                })
        );
        return;
    }

    // Check if the request is for an audio file
    const isAudioFile = url.pathname.endsWith('.mp3');
    
    // For audio files, just pass through to network
    if (isAudioFile) {
        return;
    }

    // For dynamic assets, always go to network first, fall back to cache
    if (DYNAMIC_ASSETS.some(asset => url.pathname.endsWith(asset))) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (!response || !response.ok) {
                        throw new Error('Network fetch failed');
                    }
                    // Cache the new version in the background
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME_VERSIONED).then(cache => {
                        console.log('SW.JS: Caching response for:', event.request.url);
                        cache.put(event.request, responseClone);
                    });
                    return response;
                })
                .catch(error => {
                    console.log('SW.JS: Network request failed, trying cache for:', event.request.url, error);
                    return caches.match(event.request);
                })
        );
        return;
    }

    // For other requests, check cache first, then network
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    console.log('SW.JS: Returning cached response for:', event.request.url);
                    return response;
                }
                return fetch(event.request)
                    .then(response => {
                        if (!response || !response.ok) {
                            throw new Error('Network fetch failed');
                        }
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                console.log('SW.JS: Caching response for:', event.request.url);
                                cache.put(event.request, responseToCache);
                            });
                        return response;
                    })
                    .catch(error => {
                        console.error('SW.JS: Fetch failed for:', event.request.url, error);
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
