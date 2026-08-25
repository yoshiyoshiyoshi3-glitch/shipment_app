"""
deploy.py - 投資アシストアプリを GitHub Pages にアップロードする

使い方:
  "C:\\Users\\yoshi\\AppData\\Local\\Programs\\Python\\Python312\\python.exe" toushi\\deploy.py
  （メモを付けたいとき）  ... toushi\\deploy.py "チャート表示を改善"

処理:
  1. index.html の APP_VERSION を現在日時に更新
  2. sw.js のキャッシュ名をバージョンで更新（スマホ側の更新を強制する）
  3. toushi/ 配下のファイルを GitHub に PUT
"""
import json
import base64
import urllib.request
import urllib.error
import datetime
import re
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, ROOT_DIR)
from app_config import GITHUB_REPO, APP_URL      # noqa: E402

TOKEN_FILE = os.path.join(ROOT_DIR, 'data', 'api_config.json')

# アップロードするファイル（リポジトリ上のパス, ローカルパス, テキストか）
FILES = [
    ('toushi/index.html',      'index.html',        True),
    ('toushi/sw.js',           'sw.js',             True),
    ('toushi/manifest.json',   'manifest.json',     True),
    ('toushi/watchlist.json',  'watchlist.json',    True),
    ('toushi/collect.py',      'collect.py',        True),
    ('toushi/icon-192.png',    'icon-192.png',      False),
    ('toushi/icon-512.png',    'icon-512.png',      False),
    ('toushi/icon-maskable.png', 'icon-maskable.png', False),
    ('toushi/data/market.json', os.path.join('data', 'market.json'), True),
]

note = sys.argv[1] if len(sys.argv) > 1 else ''


def load_token():
    with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)['github_token']


def get_sha(token, path):
    url = 'https://api.github.com/repos/%s/contents/%s' % (GITHUB_REPO, path)
    req = urllib.request.Request(url, headers={
        'Authorization': 'token ' + token, 'User-Agent': 'Python'})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())['sha']
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def put_file(token, path, content, sha, message):
    url = 'https://api.github.com/repos/%s/contents/%s' % (GITHUB_REPO, path)
    data = {'message': message, 'content': base64.b64encode(content).decode()}
    if sha:
        data['sha'] = sha
    req = urllib.request.Request(url, data=json.dumps(data).encode(), method='PUT', headers={
        'Authorization': 'token ' + token,
        'Content-Type': 'application/json',
        'User-Agent': 'Python'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['commit']['sha'][:12]


def stamp_version(version):
    """index.html の APP_VERSION と sw.js のキャッシュ名を書き換える"""
    idx = os.path.join(BASE_DIR, 'index.html')
    with open(idx, 'r', encoding='utf-8') as f:
        html = f.read()
    new_html = re.sub(r"var APP_VERSION='[^']*'", "var APP_VERSION='%s'" % version, html)
    if new_html == html:
        print('警告: APP_VERSION の書き換えパターンが見つかりません')
    with open(idx, 'w', encoding='utf-8') as f:
        f.write(new_html)

    sw = os.path.join(BASE_DIR, 'sw.js')
    with open(sw, 'r', encoding='utf-8') as f:
        js = f.read()
    new_js = re.sub(r"const CACHE = 'toushi-[^']*'", "const CACHE = 'toushi-%s'" % version, js)
    if new_js == js:
        print('警告: sw.js のキャッシュ名の書き換えパターンが見つかりません')
    with open(sw, 'w', encoding='utf-8') as f:
        f.write(new_js)


def main():
    token = load_token()
    version = datetime.datetime.now().strftime('%Y%m%d-%H%M')
    print('バージョン: %s' % version)
    stamp_version(version)

    msg = 'toushi: v%s%s' % (version, (' - ' + note) if note else '')
    for repo_path, local_rel, is_text in FILES:
        local = os.path.join(BASE_DIR, local_rel)
        if not os.path.exists(local):
            print('スキップ（ファイルなし）: %s' % local_rel)
            continue
        with open(local, 'rb') as f:
            content = f.read()
        sha = get_sha(token, repo_path)
        commit = put_file(token, repo_path, content, sha, msg)
        print('  アップロード完了: %-28s → %s' % (repo_path, commit))

    print('\n[完了] バージョン %s' % version)
    print('アプリURL: %stoushi/' % APP_URL)
    print('GitHub Pages に反映されるまで約1〜2分かかります。')


if __name__ == '__main__':
    main()
