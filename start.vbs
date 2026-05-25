Set sh = CreateObject("WScript.Shell")
dir = Replace(WScript.ScriptFullName, WScript.ScriptName, "")
sh.Run "powershell -ExecutionPolicy Bypass -NoProfile -File """ & dir & "server.ps1"""
