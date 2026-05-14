@echo off
setlocal
cd /d "%~dp0\.."
arnis-korea-cli.exe generate ^
  --source mock-naver ^
  --bbox "37.5955,127.0555,37.5985,127.0620" ^
  --output-dir ".\world-hufs-naver-mock" ^
  --terrain=false ^
  --interior=false ^
  --roof=true ^
  --building-mode full
