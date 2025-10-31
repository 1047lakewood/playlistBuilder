@echo off
setlocal enabledelayedexpansion

:: Prompt for folder path
set /p "folderPath=Enter the folder path: "

:: Check if folder exists
if not exist "%folderPath%" (
    echo Error: The specified folder does not exist.
    goto :eof
)

:: Count total files in subfolders
set fileCount=0
for /r "%folderPath%" %%F in (*) do (
    set "filePath=%%~dpF"
    if /i not "!filePath!" == "%folderPath%\" (
        set /a fileCount+=1
    )
)

:: Display prompt with file count
echo About to move %fileCount% files to folder "%folderPath%"
set /p "confirm=Do you want to continue? (Y/N): "
if /i not "%confirm%" == "Y" goto :eof

:: Move files from subfolders to parent folder
echo Moving files...
for /r "%folderPath%" %%F in (*) do (
    set "filePath=%%~dpF"
    if /i not "!filePath!" == "%folderPath%\" (
        move "%%F" "%folderPath%"
    )
)

echo.
echo Operation completed successfully.
echo %fileCount% files have been moved to "%folderPath%"

endlocal