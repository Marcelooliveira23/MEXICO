# PowerShell script to create desktop shortcut with Mexicana icon
$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $DesktopPath "Aircraft Inspection Analysis.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "$PSScriptRoot\run_app.bat"
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Description = "Mexicana Aircraft Inspection Analysis System"
$Shortcut.IconLocation = "$PSScriptRoot\assets\icons\mexicana_app.ico,0"
$Shortcut.Save()

Write-Host "Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "Location: $ShortcutPath" -ForegroundColor Cyan

