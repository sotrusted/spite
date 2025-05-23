const CACHE_NAME = 'spite-cache-v1';
const urlsToCache = [
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        // Cache resources one by one to handle failures gracefully
        return Promise.all(
          urlsToCache.map(url => {
            return cache.add(url).catch(err => {
              console.error('Error caching', url, err);
            });
          })
        );
      })
  );
}); 