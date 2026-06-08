const CACHE = 'shipment-20260608-2155';
const ASSETS = ['./index.html','./manifest.json','./icon-192.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
// HTML（ページ本体）はネットワーク優先：更新を確実に反映。オフライン時はキャッシュにフォールバック。
// その他のアセットはキャッシュ優先で高速表示。
self.addEventListener('fetch', e => {
  const req = e.request;
  const isHTML = req.mode === 'navigate' || (req.destination === 'document') || /index\.html$/.test(new URL(req.url).pathname);
  if (isHTML) {
    e.respondWith(
      fetch(req).then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put('./index.html', copy));
        return res;
      }).catch(() => caches.match('./index.html'))
    );
  } else {
    e.respondWith(caches.match(req).then(r => r || fetch(req)));
  }
});
