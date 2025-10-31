@echo off
setlocal enabledelayedexpansion

:: Get the current folder name to use as the artist name
for %%I in ("%CD%") do set "ARTIST_NAME=%%~nxI"
echo Setting artist metadata to: "%ARTIST_NAME%" for all MP3 files in subfolders

:: Find all MP3 files in all subfolders and process them
for /r %%F in (*.mp3) do (
    echo Processing: "%%F"
    
    :: Create a temporary metadata file - fixing the syntax issue
    echo ;FFMETADATA1 > "%%F.meta"
    echo artist=%ARTIST_NAME% >> "%%F.meta"
    
    :: Use ffmpeg to update just the metadata
    ffmpeg -hide_banner -loglevel error -i "%%F" -i "%%F.meta" -map_metadata 1 -map 0 -c copy -y "%%F.new.mp3"
    
    :: Replace the original file with the new one
    del "%%F"
    move /y "%%F.new.mp3" "%%F"
    
    :: Clean up the metadata file
    del "%%F.meta"
)

echo Done! All MP3 files have been updated with artist: "%ARTIST_NAME%"
pause