@echo off
setlocal enabledelayedexpansion

:: Check if input folder is provided
if "%~1"=="" (
    echo Please provide an input folder.
    echo Usage: %0 [input_folder]
    exit /b 1
)

set "inputFolder=%~1"
set "outputFile=folder_paths.txt"
set "tempFile=%temp%\temp_paths.txt"
set "fileCount=0"

:: Clear output file
type nul > "%outputFile%"
type nul > "%tempFile%"
echo Processing files... Please wait.

:: Process all M3U8 files in the input folder and subfolders
for /r "%inputFolder%" %%F in (*.m3u8) do (
    set /a fileCount+=1
    
    :: Use findstr to extract non-comment lines and exclude specific drive letters
    findstr /v "^#" "%%F" | findstr /v "^G: ^I: ^K: ^H:" >> "%tempFile%"
)

:: Process the collected paths
if exist "%tempFile%" (
    for /f "usebackq tokens=* delims=" %%L in ("%tempFile%") do (
        set "folderPath=%%~dpL"
        if "!folderPath:~-1!"=="\" set "folderPath=!folderPath:~0,-1!"
        echo !folderPath!>> "%outputFile%"
    )
)

:: Remove duplicate paths
if exist "%outputFile%" (
    sort "%outputFile%" /o "%tempFile%"
    type nul > "%outputFile%"
    set "lastLine="
    for /f "usebackq tokens=* delims=" %%A in ("%tempFile%") do (
        if not "%%A"=="!lastLine!" (
            echo %%A>> "%outputFile%"
            set "lastLine=%%A"
        )
    )
)

del "%tempFile%" 2>nul

echo Done! Processed %fileCount% files. Folder paths have been written to %outputFile%