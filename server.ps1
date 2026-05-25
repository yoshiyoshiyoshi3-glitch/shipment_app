$port = 8765
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$url = "http://localhost:$port/index.html"

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$port/")
try { $listener.Start() }
catch {
    Write-Host "ERROR: Cannot open port $port" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit
}

Write-Host "Server running: $url" -ForegroundColor Green
Write-Host "Close this window to stop." -ForegroundColor Yellow
Start-Process $url

$mime = @{
    ".html" = "text/html; charset=utf-8"
    ".js"   = "application/javascript"
    ".json" = "application/json"
    ".png"  = "image/png"
    ".ico"  = "image/x-icon"
}

while ($listener.IsListening) {
    $ctx  = $listener.GetContext()
    $path = $ctx.Request.Url.LocalPath
    if ($path -eq "/") { $path = "/index.html" }
    $file = Join-Path $dir $path.TrimStart("/")
    if (Test-Path $file -PathType Leaf) {
        $ext  = [IO.Path]::GetExtension($file)
        $ct   = if ($mime[$ext]) { $mime[$ext] } else { "application/octet-stream" }
        $data = [IO.File]::ReadAllBytes($file)
        $ctx.Response.ContentType     = $ct
        $ctx.Response.ContentLength64 = $data.Length
        $ctx.Response.OutputStream.Write($data, 0, $data.Length)
    } else {
        $ctx.Response.StatusCode = 404
    }
    $ctx.Response.Close()
}
