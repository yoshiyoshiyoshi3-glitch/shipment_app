# 投資アシスト（テクニカル分析＋配当・優待）

日経225の主要50銘柄を常時監視し、テクニカル分析で買い・売りシグナルを出すスマホアプリ（PWA）。
`toushi_system.xlsx`（配当・優待投資サポート）のスマホアプリ版でもあります。

**アプリURL**: https://yoshiyoshiyoshi3-glitch.github.io/shipment_app/toushi/

## 仕組み

```
GitHub Actions（平日15分おき）
   └─ toushi/collect.py
        ├─ Yahoo Finance から日足OHLCVを取得（失敗時は stooq にフォールバック）
        ├─ SMA / EMA / MACD / RSI / ボリンジャーバンド / ATR / 出来高比 を計算
        ├─ 買い・売りシグナルを判定してスコア化
        └─ toushi/data/market.json に書き出してコミット
                    ↓
GitHub Pages で配信
                    ↓
toushi/index.html（PWA）
   ├─ market.json を読んで表示
   ├─ 前回から増えたシグナルを検出 → 通知＋バッジ
   └─ Service Worker が periodicsync でアプリを閉じている間もチェック
```

株価は自前で保存せず、毎回 Yahoo Finance から1年分を取り直して計算しています。

## ファイル構成

| ファイル | 役割 |
|---|---|
| `index.html` | アプリ本体（全コード埋め込み・1ファイル構成） |
| `sw.js` | Service Worker。オフラインキャッシュとバックグラウンド通知 |
| `manifest.json` | PWA設定（ホーム画面に追加したときの見え方） |
| `collect.py` | データ収集・テクニカル分析。GitHub Actions が実行 |
| `watchlist.json` | 監視銘柄リスト。**ここを編集すると次回収集から反映** |
| `deploy.py` | GitHub Pages へのアップロード |
| `make_icon.py` | アプリアイコンの生成 |
| `data/market.json` | 収集結果（自動生成・自動コミット） |

ワークフローは `.github/workflows/market.yml`。

## よくある操作

**監視銘柄を変える** … `watchlist.json` の `stocks` を編集 → `python toushi/deploy.py`

**ローカルで動作確認**
```
python toushi/collect.py          # データを手元で作る
python -m http.server 8770        # リポジトリのルートで実行
# → http://localhost:8770/toushi/
```

**デプロイ**
```
"C:\Users\yoshi\AppData\Local\Programs\Python\Python312\python.exe" toushi\deploy.py "変更メモ"
```
`APP_VERSION` と `sw.js` のキャッシュ名は deploy.py が自動更新するので手で変える必要はありません。

## シグナルの判定ルール

スコアの合計で判定します（買い＝プラス、売り＝マイナス）。

| シグナル | 重み | 条件 |
|---|---|---|
| ゴールデン／デッドクロス | ±3 | 5日線が25日線を上／下に抜けた |
| 中期ゴールデン／デッドクロス | ±2 | 25日線が75日線を上／下に抜けた |
| 25日線かい離 | ±2 | 25日線から±12%以上離れた |
| RSI売られ／買われすぎ | ±2 | RSI(14) が30以下／70以上 |
| MACD買い／売り転換 | ±2 | ヒストグラムがゼロを跨いだ |
| ボリンジャーバンド | ±1 | 終値が±2σを超えた |
| 出来高急増 | ±1 | 25日平均の2倍以上の出来高で上昇／下落 |

合計 **±4以上**で「強い買い／売りサイン」、**±2以上**で「買い／売り検討」、それ以外は「様子見」。

## 注意

- 本アプリは投資判断を支援するツールであり、投資助言ではありません。
- **自動売買は行いません。** 発注は必ず証券会社の画面でご自身で行ってください。
- 株価は遅延データです（20分程度）。
- GitHub Actions の cron は混雑時に数分〜十数分遅れることがあります。
