@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo 起動中... しばらくお待ちください
echo.

powershell -ExecutionPolicy Bypass -NoProfile -Command ^
  "$port=8765; $dir='%~dp0'.TrimEnd('\'); " ^
  "$mime=@{'.html'='text/html; charset=utf-8';'.js'='application/javascript';'.json'='application/json';'.png'='image/png';'.ico'='image/x-icon'}; " ^
  "$listener=New-Object System.Net.HttpListener; " ^
  "$listener.Prefixes.Add('http://localhost:'+$port+'/'); " ^
  "try{ $listener.Start() } catch { Write-Host 'ポートを開けませんでした' -ForegroundColor Red; Read-Host; exit }; " ^
  "Write-Host '====================================' -ForegroundColor Green; " ^
  "Write-Host '  サーバー起動: http://localhost:'+$port+'/index.html' -ForegroundColor Cyan; " ^
  "Write-Host '  このウィンドウを閉じると停止します' -ForegroundColor Yellow; " ^
  "Write-Host '====================================' -ForegroundColor Green; " ^
  "Start-Process ('http://localhost:'+$port+'/index.html'); " ^
  "while($listener.IsListening){ " ^
    "$ctx=$listener.GetContext(); " ^
    "$path=$ctx.Request.Url.LocalPath; " ^
    "if($path -eq '/'){$path='/index.html'}; " ^
    "$file=Join-Path $dir ($path.TrimStart('/')); " ^
    "if(Test-Path $file -PathType Leaf){ " ^
      "$ext=[IO.Path]::GetExtension($file); " ^
      "$ct=if($mime[$ext]){$mime[$ext]}else{'application/octet-stream'}; " ^
      "$bytes=[IO.File]::ReadAllBytes($file); " ^
      "$ctx.Response.ContentType=$ct; " ^
      "$ctx.Response.ContentLength64=$bytes.Length; " ^
      "$ctx.Response.OutputStream.Write($bytes,0,$bytes.Length) " ^
    "}else{$ctx.Response.StatusCode=404}; " ^
    "$ctx.Response.Close() " ^
  "}"

pause
