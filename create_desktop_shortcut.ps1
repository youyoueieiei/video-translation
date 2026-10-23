# Creates a Desktop shortcut that opens the GUI with no console window.
$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbs = Join-Path $appDir "run_subtitle_translator.vbs"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "MP4 Subtitle Translator.lnk"

if (-not (Test-Path -LiteralPath $vbs)) {
    throw "Launcher not found: $vbs"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$vbs`""
$shortcut.WorkingDirectory = $appDir
$shortcut.WindowStyle = 7
$shortcut.Description = "MP4 Subtitle Translator"
$shortcut.Save()

Write-Host "Created desktop shortcut: $shortcutPath"
