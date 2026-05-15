# Troubleshooting

## 앱이 열리지 않음

- `%APPDATA%\ArnisKorea\logs\latest.log` 확인
- `arnis-korea.exe --safe-mode` 실행
- `dev-tools\arnis-korea-debug.exe` 실행

## 월드 생성 실패

- accepted layer가 비어 있는지 확인
- `reports/synthetic_osm_export_report.json` 확인
- `reports/worldgen-report.json` 확인
- `reports/world-validation.json` 확인

## 복사 실패

Minecraft saves에 같은 이름이 있으면 기본값은 덮어쓰지 않습니다. 자동 suffix가 붙은 폴더로 복사됩니다.

로그를 공유할 때 Naver key 원문이 포함되지 않았는지 확인하세요.
