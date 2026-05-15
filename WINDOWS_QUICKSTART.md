# Windows Quickstart

## 실행

1. GitHub Actions artifact `arnis-korea-1.0.0-windows_x86_64`를 내려받습니다.
2. zip을 풉니다.
3. `arnis-korea.exe`를 실행합니다.

일반 사용자는 root의 `arnis-korea.exe`만 사용합니다. 개발 진단용 실행 파일은 `dev-tools/` 아래에만 있습니다.

## 앱이 안 열릴 때

1. `dev-tools\arnis-korea-debug.exe`를 실행해 콘솔 오류를 확인합니다.
2. `%APPDATA%\ArnisKorea\logs\latest.log` 파일을 확인합니다.
3. `arnis-korea.exe --safe-mode`로 안전 모드를 실행합니다.

오류 내용을 개인 기록이나 이슈에 붙여넣기 전에 Naver Client ID, Client Secret 같은 키 원문이 포함되어 있지 않은지 확인하세요. 앱은 키 원문을 로그에 쓰지 않도록 구성되어 있습니다.

로그 위치:

```text
%APPDATA%\ArnisKorea\logs\latest.log
```

## 기본 작업 흐름

1. `프로젝트` 탭에서 프로젝트 폴더와 이름을 지정하고 `새 프로젝트`를 누릅니다.
2. `네이버 API` 탭에서 Client ID와 Client Secret을 입력하고 저장합니다.
3. `지도 범위` 탭에서 bbox를 입력하거나 `HUFS 샘플 bbox`를 누릅니다.
4. `레이어 편집` 탭에서 레이어를 선택하고 지도 영역을 클릭해 점을 추가합니다.
5. `feature 저장`을 눌러 accepted layer에 저장합니다.
6. 자동 후보를 쓸 때는 `mock 후보 생성` 또는 Static Map 분석 후보를 확인한 뒤 `suggested 승인`을 눌러 accepted layer로 옮깁니다.
7. `내보내기` 탭에서 `accepted_layers.geojson`과 `synthetic_osm_preview.json`을 생성합니다.
8. `검수/리포트` 탭에서 validation report를 확인합니다.

## v1.0 제한

v1.0은 Trace Editor Editing MVP입니다. Minecraft 월드 생성은 v1.1에서 Arnis Writer와 연결됩니다.

## 키 저장 위치

```text
%APPDATA%\ArnisKorea\secrets.json
```

이 파일은 artifact에 포함되지 않습니다. 프로젝트 폴더에도 저장하지 않습니다.
