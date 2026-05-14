@echo off
cd /d "%~dp0"
arnis-korea-cli.exe plan-static --bbox-file ".\sample_bbox_hufs.json"
echo.
pause
