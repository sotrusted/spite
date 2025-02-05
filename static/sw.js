const CACHE_NAME = 'pwa-cache-v2';

// Separate static assets that rarely change
const STATIC_ASSETS = [
    '/static/media/anon.webp',
    '/static/media/spite.gif',
    '/static/media/spite-logo.webp',
    '/static/media/spitemagazine.gif',
    '/static/sounds/message.mp3',
    '/static/sounds/join.mp3',
    '/static/sounds/notification-sound.mp3',
    '/static/sounds/jinglebell-sound.mp3',
    '/static/sounds/shining-sound.mp3',
    '/static/sounds/harp.mp3',
    '/static/sounds/harp-flourish-sound.mp3',
    '/static/sounds/sword-sound.mp3',
    '/static/sounds/leave.mp3',
    '/static/sounds/send.mp3',
];

// Dynamic assets that need frequent updates
const DYNAMIC_ASSETS = [
    '/static/css/styles.css',
    '/static/js/modules/utility_functions.js',
];

// External resources to bypass service worker
const BYPASS_URLS = [
    'fonts.googleapis.com',
    'stackpath.bootstrapcdn.com',
    'fonts.gstatic.com',
    'js.stripe.com',
    'unpkg.com',
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
    '.html',  // Any HTML file
    '/post/',  // Add this for post detail pages
    '/comment/',  // Add this for comment detail pages
    '/loading/',  // Add this for loading screen
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
            fetch(event.request)
                .then(response => {
                    if (!response || response.status !== 200) {
                        throw new Error(`Network response was not ok: ${response.status}`);
                    }
                    
                    const responseToCache = response.clone();

                    // Cache successful responses
                    caches.open(CACHE_NAME)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        })
                        .catch(err => {
                            console.warn('SW.JS: Failed to cache dynamic content:', err);
                        });

                    return response;
                })
                .catch(error => {
                    console.log('SW.JS: Network failed, checking cache for:', url.pathname);
                    
                    return caches.match(event.request)
                        .then(cachedResponse => {
                            if (cachedResponse) {
                                console.log('SW.JS: Serving from cache:', url.pathname);
                                return cachedResponse;
                            }
                            
                            // If no cache, try the homepage as fallback
                            return caches.match('/')
                                .then(homepageResponse => {
                                    if (homepageResponse) {
                                        return homepageResponse;
                                    }
                                    // Last resort - error page
                                    return new Response('Content temporarily unavailable', {
                                        status: 503,
                                        headers: {
                                            'Content-Type': 'text/html'
                                        }
                                    });
                                });
                        });
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
    event.waitUntil(
        Promise.all([
            // Clear old caches
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => caches.delete(cacheName))
                );
            }),
            // Claim clients
            self.clients.claim()
        ])
    );
});
