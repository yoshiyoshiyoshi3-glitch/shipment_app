# 出荷伝票アプリ サーバー起動（PowerShell版）
$Port = 8765
$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path

$MIME = @{
    ".html" = "text/html; charset=utf-8"
    ".js"   = "application/javascript"
    ".json" = "application/json"
    ".png"  = "image/png"
    ".ico"  = "image/x-icon"
}

function Get-LocalIP {
    (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback" -and $_.IPAddress -notmatch "^169" } | Select-Object -First 1).IPAddress
}

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
try {
    $listener.Prefixes.Add("http://+:$Port/")
} catch {}

try { $listener.Start() }
catch {
    Write-Host "エラー: ポート $Port を開けませんでした。管理者として実行してみてください。" -ForegroundColor Red
    pause
    exit
}

$ip = Get-LocalIP
Write-Host ("=" * 50) -ForegroundColor Green
Write-Host "  出荷伝票サーバー起動中" -ForegroundColor Green
Write-Host "  PC:      http://localhost:$Port/index.html" -ForegroundColor Cyan
Write-Host "  Android: http://${ip}:$Port/index.html" -ForegroundColor Yellow
Write-Host ("=" * 50) -ForegroundColor Green
Write-Host "  Ctrl+C で停止"
Write-Host ""

Start-Process "http://localhost:$Port/index.html"

while ($listener.IsListening) {
    $ctx = $listener.GetContext()
    $req = $ctx.Request
    $res = $ctx.Response
    $urlPath = $req.Url.LocalPath
    if ($urlPath -eq "/") { $urlPath = "/index.html" }
    $filePath = Join-Path $Dir $urlPath.TrimStart("/")
    if (Test-Path $filePath -PathType Leaf) {
        $ext = [System.IO.Path]::GetExtension($filePath)
        $ct = if ($MIME[$ext]) { $MIME[$ext] } else { "application/octet-stream" }
        $bytes = [System.IO.File]::ReadAllBytes($filePath)
        $res.ContentType = $ct
        $res.ContentLength64 = $bytes.Length
        $res.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
        $res.StatusCode = 404
    }
    $res.Close()
}
