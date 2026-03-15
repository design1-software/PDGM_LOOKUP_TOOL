const CACHE_VERSION = '{{ version }}';
const CACHE_NAME = `pdgm-cache-v${CACHE_VERSION}`;
const urlsToCache = [
    '/',
    '/static/style.css',
    '/static/ReferralMate_CCFTF_combined.png'
];

// Install event: pre-cache assets
self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => Promise.all(
                urlsToCache.map(url => {
                    const req = new Request(url, {cache: 'reload'});
                    return cache.add(req).catch(err => {
                        console.warn(`Failed to cache ${url}:`, err);
                    });
                })
            ))
            .catch(err => console.error('SW install failed:', err))
    );
});

// Activate event: clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

// Fetch event: network-first for navigation, cache fallback
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    // Never cache auth or API endpoints; always hit network
    if (url.pathname.startsWith('/auth/') || url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }
    if (event.request.mode === 'navigate') {
        event.respondWith(
            (async () => {
                try {
                    const resp = await fetch(event.request);
                    const copy = resp.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        if (event.request.method === 'GET') {
                            cache.put(event.request, copy);
                        }
                    });
                    return resp;
                } catch (err) {
                    // Network failed, try cache
                    const cached = await caches.match(event.request);
                    if (cached) return cached;
                    // Optionally: return a fallback offline page for navigation
                    return new Response('<h1>Offline</h1>', {
                        status: 503,
                        headers: {'Content-Type': 'text/html'}
                    });
                }
            })()
        );
        return;
    }
    // For all other requests: cache-first, network fallback
    event.respondWith(
        caches.open(CACHE_NAME).then(async cache => {
            const res = await cache.match(event.request);
            if (res) return res;
            try {
                const networkRes = await fetch(event.request);
                // The Cache API typically only caches GET and HEAD requests reliably across browsers.
                // Attempting to cache other methods like POST will throw
                // a `TypeError: Request method 'POST' is unsupported`.
                if (event.request.method === 'GET') {
                    cache.put(event.request, networkRes.clone());
                }
                return networkRes;
            } catch (err) {
                // Could not fetch, no cache available
                return new Response('', {status: 503, statusText: 'Service Unavailable'});
            }
        })
    );
});

// Message event: support skipWaiting
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    if (event.ports && event.ports[0]) {
        event.ports[0].postMessage({status: 'ack'});
    }
});
