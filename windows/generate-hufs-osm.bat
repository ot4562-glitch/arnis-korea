@echo off
cd /d "%~dp0"
arnis-korea-cli.exe generate --bbox "37.5955,127.0555,37.5985,127.0620" --output-dir ".\world-hufs" --source osm --terrain --interior=false --roof=true
echo.
pause
