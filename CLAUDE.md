# 出荷伝票アプリ（Sakai Floric MITSUSE）開発コンテキスト

このリポジトリは GitHub Pages で **2つのアプリ** をホストしている。

## ① 出荷伝票アプリ（ルート）
花の出荷管理Webアプリ。`index.html` 1ファイル構成（全コード埋め込み）。
スマートフォン（主にAndroid Chrome）で使用。

- メインアプリ: `index.html`
- デプロイ: `"C:\Users\yoshi\AppData\Local\Programs\Python\Python312\python.exe" upload.py`

## ② 投資アシスト（`toushi/`）
日経225主要銘柄のテクニカル分析＋買い売りアラート＋配当優待管理のPWA。
詳細は `toushi/README.md` を参照。

- アプリ本体: `toushi/index.html`
- データ収集: `toushi/collect.py`（`.github/workflows/market.yml` が平日15分おきに実行）
- デプロイ: `... python.exe toushi\deploy.py`
- **`.gitignore` の `/data/` は先頭スラッシュ必須**（`data/` だと `toushi/data/` まで無視され、
  Actions が market.json をコミットできなくなる）

## 共通
- 設定: `data\api_config.json`（github_token, claude_api_key, imap_password — チャットに貼らない）
- 2つのアプリは Service Worker のスコープが別（`/` と `/toushi/`）なので干渉しない

## コンテキストが圧縮されて再開した場合
作業中のタスクがあれば、前回の続きから再開する。
ユーザーが「再開」と言ったら、直前の未完了作業を確認してすぐ再開すること。

## 許可設定
- ツール使用・ファイル編集・PowerShell/Bashコマンド実行はすべて自動承認
- デプロイ（upload.py実行）も自動承認

## 開発上の注意
- `continuous=false` 方式のSR（音声認識）を使用（モバイル互換）
- デプロイ後はGitHub Pages反映まで1〜2分かかる
- APP_VERSION は upload.py / toushi\deploy.py が自動更新するため手動変更不要
- 投資アプリは自動発注しない。売買を代行する機能は追加しないこと（判断支援のみ）
