# Creates a Desktop shortcut to the subtitle translator GUI.
$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat = Join-Path $appDir "run_subtitle_translator.bat"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "MP4字幕翻译.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $bat
$shortcut.WorkingDirectory = $appDir
$shortcut.WindowStyle = 7
$shortcut.Description = "MP4 字幕翻译工具"
$shortcut.Save()

Write-Host "已创建桌面快捷方式: $shortcutPath"
