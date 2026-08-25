/* 投資アシスト Service Worker
   ・アプリ本体をキャッシュしてオフラインでも開けるようにする
   ・periodicsync でアプリを閉じている間もシグナルをチェックして通知する */
const CACHE = 'toushi-dev';
const ASSETS = ['./index.html', './manifest.json', './icon-192.png', './icon-512.png'];

const STATE_CACHE = 'toushi-state-v1';
const STATE_URL   = './__state.json';

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(k => k !== CACHE && k !== STATE_CACHE).map(k => caches.delete(k))
  )));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  const isHTML   = req.mode === 'navigate' || req.destination === 'document';
  const isMarket = /market\.json$/.test(url.pathname);

  // 本体と株価データはネットワーク優先（常に最新を見せ、圏外ならキャッシュ）
  if (isHTML || isMarket) {
    const key = isHTML ? './index.html' : './data/market.json';
    e.respondWith(
      fetch(req).then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(key, copy));
        return res;
      }).catch(() => caches.match(key))
    );
  } else {
    e.respondWith(caches.match(req).then(r => r || fetch(req)));
  }
});

/* ── 既読状態（ページ側と共有） ───────────────────────── */
function readState() {
  return caches.open(STATE_CACHE)
    .then(c => c.match(STATE_URL))
    .then(r => r ? r.json() : null)
    .then(s => s || { seen: {}, th: 2, scope: 'all', held: [] })
    .catch(() => ({ seen: {}, th: 2, scope: 'all', held: [] }));
}
function writeState(s) {
  return caches.open(STATE_CACHE)
    .then(c => c.put(STATE_URL, new Response(JSON.stringify(s), {
      headers: { 'Content-Type': 'application/json' }
    })))
    .catch(() => {});
}

/* ── バックグラウンドでのシグナルチェック ───────────────── */
function checkMarket() {
  return Promise.all([
    fetch('./data/market.json?t=' + Date.now(), { cache: 'no-store' }).then(r => r.json()),
    readState()
  ]).then(([mk, st]) => {
    const seen  = st.seen || {};
    const th    = st.th || 2;
    const scope = st.scope || 'all';
    const held  = st.held || [];
    if (!Object.keys(seen).length) return;      // 初回は一斉通知しない

    const fresh = [];
    mk.items.filter(x => x.kind === 'stock').forEach(it => {
      if (Math.abs(it.score) < th) return;
      if (scope === 'held' && held.indexOf(it.code) < 0) return;
      it.signals.forEach(s => {
        const k = it.code + '|' + it.date + '|' + s.label;
        if (seen[k]) return;
        seen[k] = 1;
        fresh.push({ it, s });
      });
    });

    const keys = Object.keys(seen);
    if (keys.length > 500) {
      const trimmed = {};
      keys.slice(-500).forEach(k => { trimmed[k] = 1; });
      st.seen = trimmed;
    } else {
      st.seen = seen;
    }

    return writeState(st).then(() => {
      if (!fresh.length) return;
      let title, body;
      if (fresh.length === 1) {
        const f = fresh[0];
        title = (f.s.kind === 'buy' ? '📈 買いサイン' : '📉 売りサイン') + '：' + f.it.name;
        body  = f.s.label + '\n¥' + Math.round(f.it.price).toLocaleString('ja-JP') +
                '（' + (f.it.changePct > 0 ? '+' : '') + f.it.changePct + '%）';
      } else {
        const buys = fresh.filter(x => x.s.kind === 'buy').length;
        title = '🔔 新しいシグナル ' + fresh.length + '件';
        body  = '買い ' + buys + '件 / 売り ' + (fresh.length - buys) + '件　タップして確認';
      }
      if (self.registration.setAppBadge) self.registration.setAppBadge(fresh.length).catch(() => {});
      return self.registration.showNotification(title, {
        body, icon: './icon-192.png', badge: './icon-192.png',
        tag: 'toushi-signal', renotify: true, data: { url: './index.html' }
      });
    });
  }).catch(() => {});
}

self.addEventListener('periodicsync', e => {
  if (e.tag === 'market-check') e.waitUntil(checkMarket());
});
self.addEventListener('sync', e => {
  if (e.tag === 'market-check') e.waitUntil(checkMarket());
});
self.addEventListener('message', e => {
  if (e.data && e.data.type === 'check') e.waitUntil(checkMarket());
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) {
        if (c.url.indexOf('/toushi/') >= 0) return c.focus();
      }
      return clients.openWindow('./index.html');
    })
  );
});
