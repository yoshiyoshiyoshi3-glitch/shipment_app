# -*- coding: utf-8 -*-
"""
collect.py - 株価テクニカル情報の自動収集＋分析

GitHub Actions から定期実行され、watchlist.json の銘柄について
  1. 日足OHLCVを取得（Yahoo Finance → 失敗時 stooq にフォールバック）
  2. テクニカル指標を計算（SMA/EMA/MACD/RSI/BB/ATR/出来高）
  3. 買い・売りシグナルを判定してスコア化
  4. data/market.json に書き出す
アプリ（index.html）はこの market.json だけを読む。

ローカル実行:
  python toushi/collect.py
"""
import json
import os
import time
import urllib.request
import urllib.error
import urllib.parse
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WATCHLIST = os.path.join(BASE_DIR, 'watchlist.json')
OUT_DIR = os.path.join(BASE_DIR, 'data')
OUT_FILE = os.path.join(OUT_DIR, 'market.json')

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0 Safari/537.36')
HISTORY_DAYS = 130          # market.json に残す日足の本数
JST = datetime.timezone(datetime.timedelta(hours=9))


# ────────────────────────────────────────────────────────────
# データ取得
# ────────────────────────────────────────────────────────────
def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': '*/*',
        'Accept-Language': 'ja,en;q=0.8',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_yahoo(code):
    """Yahoo Finance のチャートAPIから日足を取得。[(date, o, h, l, c, v), ...]"""
    symbol = code if code.startswith('^') else code + '.T'
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/'
           + urllib.parse.quote(symbol)
           + '?interval=1d&range=1y&includePrePost=false')
    raw = json.loads(_get(url))
    result = raw['chart']['result'][0]
    stamps = result['timestamp']
    q = result['indicators']['quote'][0]
    rows = []
    for i, ts in enumerate(stamps):
        o, h, l, c, v = q['open'][i], q['high'][i], q['low'][i], q['close'][i], q['volume'][i]
        if c is None:
            continue
        d = datetime.datetime.fromtimestamp(ts, JST).strftime('%Y-%m-%d')
        rows.append((d, o or c, h or c, l or c, c, v or 0))
    return rows


def fetch_stooq(code):
    """stooq の日足CSV（Yahooが失敗したときのフォールバック）"""
    if code.startswith('^'):
        raise ValueError('stooq は指数の代替取得に未対応')
    url = 'https://stooq.com/q/d/l/?s=%s.jp&i=d' % code.lower()
    text = _get(url).decode('utf-8', 'replace').strip().splitlines()
    rows = []
    for line in text[1:]:
        parts = line.split(',')
        if len(parts) < 6:
            continue
        try:
            d = parts[0]
            o, h, l, c = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            v = float(parts[5]) if parts[5] else 0
        except ValueError:
            continue
        rows.append((d, o, h, l, c, v))
    return rows[-260:]


def fetch(code):
    """Yahoo優先、失敗したら stooq。両方だめなら例外。"""
    errors = []
    for attempt in range(3):
        try:
            rows = fetch_yahoo(code)
            if len(rows) >= 30:
                return rows, 'yahoo'
            errors.append('yahoo: 本数不足 %d' % len(rows))
            break
        except Exception as e:                      # 429/503 は待って再試行
            errors.append('yahoo: %s' % e)
            time.sleep(2 + attempt * 3)
    try:
        rows = fetch_stooq(code)
        if len(rows) >= 30:
            return rows, 'stooq'
        errors.append('stooq: 本数不足 %d' % len(rows))
    except Exception as e:
        errors.append('stooq: %s' % e)
    raise RuntimeError(' / '.join(errors))


# ────────────────────────────────────────────────────────────
# テクニカル指標
# ────────────────────────────────────────────────────────────
def sma(values, period):
    """単純移動平均。値が足りない位置は None。"""
    out = [None] * len(values)
    total = 0.0
    for i, v in enumerate(values):
        total += v
        if i >= period:
            total -= values[i - period]
        if i >= period - 1:
            out[i] = total / period
    return out


def ema(values, period):
    """指数移動平均。最初の period 本は単純平均で初期化する。"""
    out = [None] * len(values)
    if len(values) < period:
        return out
    k = 2.0 / (period + 1)
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(values, period=14):
    """RSI（Wilder方式）"""
    out = [None] * len(values)
    if len(values) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains += max(diff, 0.0)
        losses += max(-diff, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    out[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(diff, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-diff, 0.0)) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out


def macd(values, fast=12, slow=26, signal=9):
    """MACD / シグナル / ヒストグラム"""
    ef, es = ema(values, fast), ema(values, slow)
    line = [None if (ef[i] is None or es[i] is None) else ef[i] - es[i]
            for i in range(len(values))]
    valid = [v for v in line if v is not None]
    sig_valid = ema(valid, signal)
    offset = len(line) - len(valid)
    sig = [None] * len(line)
    for i, v in enumerate(sig_valid):
        sig[offset + i] = v
    hist = [None if (line[i] is None or sig[i] is None) else line[i] - sig[i]
            for i in range(len(line))]
    return line, sig, hist


def bollinger(values, period=20, mult=2.0):
    """ボリンジャーバンド（中心線・上限・下限）"""
    mid = sma(values, period)
    upper, lower = [None] * len(values), [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        m = mid[i]
        var = sum((x - m) ** 2 for x in window) / period
        sd = var ** 0.5
        upper[i], lower[i] = m + mult * sd, m - mult * sd
    return mid, upper, lower


def atr(highs, lows, closes, period=14):
    """ATR（平均真の値幅）。ボラティリティの目安に使う。"""
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i],
                       abs(highs[i] - closes[i - 1]),
                       abs(lows[i] - closes[i - 1])))
    return sma(trs, period)


# ────────────────────────────────────────────────────────────
# シグナル判定
# ────────────────────────────────────────────────────────────
def crossed_up(a, b, i):
    """i 日目に系列 a が系列 b を下から上に抜けたか"""
    if i < 1:
        return False
    for s in (a[i], b[i], a[i - 1], b[i - 1]):
        if s is None:
            return False
    return a[i - 1] <= b[i - 1] and a[i] > b[i]


def analyze(rows):
    """OHLCVから指標とシグナルを組み立てる。"""
    closes = [r[4] for r in rows]
    highs = [r[2] for r in rows]
    lows = [r[3] for r in rows]
    vols = [r[5] for r in rows]
    i = len(closes) - 1

    s5, s25, s75 = sma(closes, 5), sma(closes, 25), sma(closes, 75)
    r14 = rsi(closes, 14)
    m_line, m_sig, m_hist = macd(closes)
    bb_mid, bb_up, bb_low = bollinger(closes, 20, 2.0)
    a14 = atr(highs, lows, closes, 14)
    v25 = sma(vols, 25)

    price = closes[i]
    prev = closes[i - 1] if i >= 1 else price
    signals = []

    def add(kind, weight, label, detail):
        signals.append({'kind': kind, 'w': weight, 'label': label, 'detail': detail})

    # --- 移動平均のクロス ---
    if crossed_up(s5, s25, i):
        add('buy', 3, 'ゴールデンクロス', '5日線が25日線を上抜けました（上昇トレンド転換のサイン）')
    if crossed_up(s25, s5, i):
        add('sell', 3, 'デッドクロス', '5日線が25日線を下抜けました（下降トレンド転換のサイン）')
    if s25[i] and s75[i]:
        if crossed_up(s25, s75, i):
            add('buy', 2, '中期ゴールデンクロス', '25日線が75日線を上抜けました（中期の上昇転換）')
        if crossed_up(s75, s25, i):
            add('sell', 2, '中期デッドクロス', '25日線が75日線を下抜けました（中期の下降転換）')

    # --- 25日線からの乖離・位置 ---
    if s25[i]:
        dev = (price - s25[i]) / s25[i] * 100
        if dev <= -12:
            add('buy', 2, '25日線から売られすぎ', '25日線より%.1f%%下。反発を狙える水準です' % dev)
        elif dev >= 12:
            add('sell', 2, '25日線から買われすぎ', '25日線より+%.1f%%上。過熱感があります' % dev)

    # --- RSI ---
    if r14[i] is not None:
        if r14[i] <= 30:
            add('buy', 2, 'RSI売られすぎ', 'RSI %.0f（30以下）。反発しやすい水準です' % r14[i])
        elif r14[i] >= 70:
            add('sell', 2, 'RSI買われすぎ', 'RSI %.0f（70以上）。利益確定を検討する水準です' % r14[i])

    # --- MACD ---
    if m_hist[i] is not None and m_hist[i - 1] is not None:
        if m_hist[i - 1] <= 0 < m_hist[i]:
            add('buy', 2, 'MACD買い転換', 'MACDがシグナルを上抜けました')
        elif m_hist[i - 1] >= 0 > m_hist[i]:
            add('sell', 2, 'MACD売り転換', 'MACDがシグナルを下抜けました')

    # --- ボリンジャーバンド ---
    if bb_low[i] and price < bb_low[i]:
        add('buy', 1, 'BB下限割れ', 'ボリンジャーバンド−2σを下回りました')
    if bb_up[i] and price > bb_up[i]:
        add('sell', 1, 'BB上限超え', 'ボリンジャーバンド+2σを上回りました')

    # --- 出来高 ---
    vol_ratio = (vols[i] / v25[i]) if (v25[i] and v25[i] > 0) else None
    if vol_ratio and vol_ratio >= 2.0:
        if price > prev:
            add('buy', 1, '出来高急増（上昇）', '25日平均の%.1f倍の出来高で上昇。買いが集まっています' % vol_ratio)
        elif price < prev:
            add('sell', 1, '出来高急増（下落）', '25日平均の%.1f倍の出来高で下落。売りが出ています' % vol_ratio)

    score = sum(s['w'] if s['kind'] == 'buy' else -s['w'] for s in signals)
    if score >= 4:
        verdict, vlabel = 'strong_buy', '強い買いサイン'
    elif score >= 2:
        verdict, vlabel = 'buy', '買い検討'
    elif score <= -4:
        verdict, vlabel = 'strong_sell', '強い売りサイン'
    elif score <= -2:
        verdict, vlabel = 'sell', '売り検討'
    else:
        verdict, vlabel = 'neutral', '様子見'

    # トレンド（25日線と75日線の並び）
    if s25[i] and s75[i]:
        trend = 'up' if s25[i] > s75[i] else 'down'
    else:
        trend = 'flat'

    def rd(v, n=2):
        return None if v is None else round(v, n)

    hist_rows = rows[-HISTORY_DAYS:]

    return {
        'price': rd(price),
        'prevClose': rd(prev),
        'change': rd(price - prev),
        'changePct': rd((price - prev) / prev * 100 if prev else 0),
        'volume': int(vols[i]),
        'date': rows[i][0],
        'trend': trend,
        'score': score,
        'verdict': verdict,
        'verdictLabel': vlabel,
        'signals': signals,
        'ind': {
            'sma5': rd(s5[i]), 'sma25': rd(s25[i]), 'sma75': rd(s75[i]),
            'rsi': rd(r14[i], 1),
            'macd': rd(m_line[i], 3), 'macdSignal': rd(m_sig[i], 3), 'macdHist': rd(m_hist[i], 3),
            'bbUpper': rd(bb_up[i]), 'bbMid': rd(bb_mid[i]), 'bbLower': rd(bb_low[i]),
            'atr': rd(a14[i]),
            'volRatio': rd(vol_ratio, 2),
            'dev25': rd((price - s25[i]) / s25[i] * 100, 1) if s25[i] else None,
        },
        # チャート用の日付と終値だけ渡す。移動平均はアプリ側で計算する
        # （15分おきにコミットするため、JSONは可能な限り小さくしておく）
        'hist': {
            'd': [r[0][5:] for r in hist_rows],          # "MM-DD"
            'c': [rd(r[4]) for r in hist_rows],
        },
    }


# ────────────────────────────────────────────────────────────
# メイン
# ────────────────────────────────────────────────────────────
def main():
    with open(WATCHLIST, 'r', encoding='utf-8') as f:
        wl = json.load(f)

    targets = [(e, 'index') for e in wl.get('index', [])] + \
              [(e, 'stock') for e in wl.get('stocks', [])]

    items, errors = [], []
    for entry, kind in targets:
        code, name = entry['code'], entry['name']
        try:
            rows, source = fetch(code)
            data = analyze(rows)
            data.update({'code': code, 'name': name,
                         'sector': entry.get('sector', ''),
                         'kind': kind, 'source': source})
            items.append(data)
            print('OK   %-8s %-24s %8s  %s(%+d)' %
                  (code, name, data['price'], data['verdictLabel'], data['score']))
        except Exception as e:
            errors.append({'code': code, 'name': name, 'error': str(e)[:200]})
            print('FAIL %-8s %-24s %s' % (code, name, str(e)[:120]))
        time.sleep(0.4)     # Yahoo へ連続アクセスしすぎない

    now = datetime.datetime.now(JST)
    stocks = [x for x in items if x['kind'] == 'stock']
    payload = {
        'updated': now.strftime('%Y-%m-%d %H:%M'),
        'updatedIso': now.isoformat(),
        'count': len(items),
        'summary': {
            'buy': len([x for x in stocks if x['verdict'] in ('buy', 'strong_buy')]),
            'sell': len([x for x in stocks if x['verdict'] in ('sell', 'strong_sell')]),
            'neutral': len([x for x in stocks if x['verdict'] == 'neutral']),
            'up': len([x for x in stocks if (x['changePct'] or 0) > 0]),
            'down': len([x for x in stocks if (x['changePct'] or 0) < 0]),
        },
        'items': items,
        'errors': errors,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    size_kb = os.path.getsize(OUT_FILE) / 1024
    print('\n%s に書き出しました（%d銘柄 / %.0f KB / 失敗 %d件）'
          % (OUT_FILE, len(items), size_kb, len(errors)))


if __name__ == '__main__':
    main()
