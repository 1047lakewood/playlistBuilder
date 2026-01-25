@echo off
echo Deploying Playlist Builder...

:: Step 1: Import config from deployment to dev
echo Importing config.json from deployment...
copy /Y "C:\Users\Admin\Desktop\Work\Playlist Builder 2\config.json" "G:\Misc\Dev\playlistBuilder\config.json"

:: Step 2: Copy code to deployment directory
echo Copying Python files...
copy /Y "G:\Misc\Dev\playlistBuilder\*.py" "C:\Users\Admin\Desktop\Work\Playlist Builder 2\"

echo Copying models folder...
xcopy /E /Y /I "G:\Misc\Dev\playlistBuilder\models" "C:\Users\Admin\Desktop\Work\Playlist Builder 2\models"

echo Copying PlaylistService folder...
xcopy /E /Y /I "G:\Misc\Dev\playlistBuilder\PlaylistService" "C:\Users\Admin\Desktop\Work\Playlist Builder 2\PlaylistService"

echo Deploy complete!

:: Pause unless "nopause" argument is passed
if /I NOT "%1"=="nopause" pause
