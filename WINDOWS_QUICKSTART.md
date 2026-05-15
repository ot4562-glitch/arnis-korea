# Windows Quickstart

## 실행

1. Actions artifact `arnis-korea-2.0.0-private-final-windows_x86_64`를 내려받습니다.
2. zip을 풉니다.
3. `arnis-korea.exe`를 더블클릭합니다.

## 기본 흐름

1. `프로젝트` 탭에서 새 프로젝트를 만듭니다.
2. `네이버 API` 탭에서 Client ID/Secret을 저장하고 테스트합니다.
3. `지도 범위` 탭에서 bbox와 스폰포인트를 정합니다.
4. `네이버 API` 탭에서 Static Map 배경을 다운로드합니다. 저장/분석 동의가 필요합니다.
5. `레이어 편집` 탭에서 도로/건물/수역/녹지/철도/스폰포인트를 그립니다.
6. suggested 후보는 직접 확인한 뒤 승인해야 accepted layer가 됩니다.
7. `최종 생성 마법사` 탭에서 프로젝트 상태 체크, synthetic OSM 생성, 월드 생성을 순서대로 실행합니다.
8. `playable_world/<world_name>`만 Minecraft saves로 복사합니다.

## 앱이 안 열릴 때

1. `dev-tools\arnis-korea-debug.exe`를 실행합니다.
2. `%APPDATA%\ArnisKorea\logs\latest.log`를 확인합니다.
3. `arnis-korea.exe --safe-mode`를 실행합니다.

로그나 이슈 내용 공유 전 Naver 키 원문이 들어 있지 않은지 확인하세요.

## 제한

- 개인 개발용이며 공개 배포용이 아닙니다.
- 네이버 공식 API 무료 사용량 범위 안에서 사용하세요.
- 월드 생성 품질은 accepted layer trace 품질에 좌우됩니다.

## AI Trace Worker

AI Trace는 Windows EXE 내부 모델이 아니라 OCI 내부 worker 또는 dev-tools CLI로 실행합니다. GUI는 분석 패키지를 내보내고 결과를 suggested 후보로 가져옵니다. 사용자가 승인한 accepted layer만 월드 생성에 사용됩니다.
