#!/usr/bin/env python3
"""
出荷伝票アプリ — ローカルサーバー起動スクリプト
Androidで使うには: このスクリプトをダブルクリック → 表示されたURLをAndroidのChromeで開く
"""
import http.server, socketserver, socket, os, webbrowser, threading, time

PORT = 8765
DIR = os.path.dirname(os.path.abspath(__file__))

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)
    def log_message(self, format, *args):
        pass  # suppress access logs

if __name__ == "__main__":
    ip = get_local_ip()
    url = f"http://{ip}:{PORT}/index.html"
    print("=" * 50)
    print(f"  出荷伝票サーバー起動中")
    print(f"  PC: http://localhost:{PORT}/index.html")
    print(f"  Android用URL: {url}")
    print(f"  (PCとAndroidが同じWi-Fiに接続されている必要があります)")
    print("=" * 50)
    print()
    print("  Androidの手順:")
    print(f"  1. 上記URLをAndroidのChromeで開く")
    print(f"  2. Chromeメニュー →「ホーム画面に追加」でアプリ化できます")
    print()
    print("  Ctrl+C で停止")
    print()
    # QRコード (テキストベース)
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make()
        qr.print_ascii(invert=True)
    except ImportError:
        print(f"  ※ QRコードを表示するには: pip install qrcode")
        print(f"    Android URL: {url}")
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        threading.Thread(target=lambda: (time.sleep(1), webbrowser.open(f"http://localhost:{PORT}/index.html")), daemon=True).start()
        httpd.serve_forever()
