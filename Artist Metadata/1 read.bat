@echo off
setlocal enabledelayedexpansion

echo MP3 Artist Metadata Scanner
echo -------------------------
echo Scanning for MP3 files in current directory and all subfolders...
echo.

:: Create a temporary PowerShell script
echo $mp3s = Get-ChildItem -Path . -Filter *.mp3 -Recurse > "%TEMP%\getmp3info.ps1"
echo if ($mp3s.Count -eq 0) { >> "%TEMP%\getmp3info.ps1"
echo   Write-Host "No MP3 files found." >> "%TEMP%\getmp3info.ps1"
echo   exit >> "%TEMP%\getmp3info.ps1"
echo } >> "%TEMP%\getmp3info.ps1"
echo Write-Host "Found $($mp3s.Count) MP3 files." >> "%TEMP%\getmp3info.ps1"
echo Write-Host "" >> "%TEMP%\getmp3info.ps1"
echo foreach ($file in $mp3s) { >> "%TEMP%\getmp3info.ps1"
echo   $shell = New-Object -COMObject Shell.Application >> "%TEMP%\getmp3info.ps1"
echo   $folder = $shell.Namespace($file.DirectoryName) >> "%TEMP%\getmp3info.ps1"
echo   $item = $folder.ParseName($file.Name) >> "%TEMP%\getmp3info.ps1"
echo   $artist = $folder.GetDetailsOf($item, 13) >> "%TEMP%\getmp3info.ps1"
echo   if ($artist -eq "") { $artist = "Unknown Artist" } >> "%TEMP%\getmp3info.ps1"
echo   $title = $folder.GetDetailsOf($item, 21) >> "%TEMP%\getmp3info.ps1"
echo   if ($title -eq "") { $title = $file.BaseName } >> "%TEMP%\getmp3info.ps1"
echo   Write-Host "File: $($file.FullName)" >> "%TEMP%\getmp3info.ps1"
echo   Write-Host "Artist: $artist" >> "%TEMP%\getmp3info.ps1"
echo   Write-Host "Title: $title" >> "%TEMP%\getmp3info.ps1"
echo   Write-Host "" >> "%TEMP%\getmp3info.ps1"
echo } >> "%TEMP%\getmp3info.ps1"

:: Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%TEMP%\getmp3info.ps1"

:: Clean up
del "%TEMP%\getmp3info.ps1" > nul

echo -------------------------
echo Scan complete.
echo.
pause