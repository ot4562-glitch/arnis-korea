# Windows Quickstart

## 실행

1. GitHub Actions artifact `arnis-korea-1.1.0-windows_x86_64`를 내려받습니다.
2. zip을 풉니다.
3. `arnis-korea.exe`를 실행합니다.

일반 사용자는 root의 `arnis-korea.exe`만 사용합니다. 개발 진단용 실행 파일은 `dev-tools/` 아래에만 있습니다.

## 앱이 안 열릴 때

1. `dev-tools\arnis-korea-debug.exe`를 실행해 콘솔 오류를 확인합니다.
2. `%APPDATA%\ArnisKorea\logs\latest.log` 파일을 확인합니다.
3. `arnis-korea.exe --safe-mode`로 안전 모드를 실행합니다.

오류 내용을 개인 기록이나 이슈에 붙여넣기 전에 Naver Client ID, Client Secret 같은 키 원문이 포함되어 있지 않은지 확인하세요.

로그 위치:

```text
%APPDATA%\ArnisKorea\logs\latest.log
```

## 기본 작업 흐름

1. `프로젝트` 탭에서 프로젝트 폴더와 이름을 지정하고 `새 프로젝트`를 누릅니다.
2. `네이버 API` 탭에서 Client ID와 Client Secret을 입력하고 저장합니다.
3. `지도 범위` 탭에서 bbox와 스폰포인트를 확인합니다.
4. `레이어 편집` 탭에서 레이어를 직접 그리거나 suggested 후보를 승인합니다.
5. `내보내기` 탭에서 `accepted_layers.geojson`과 `synthetic_osm.json`을 생성합니다.
6. `월드 생성` 탭에서 월드 이름, roof/interior/scale 옵션을 확인하고 `월드 생성`을 누릅니다.
7. 생성된 `project_dir\playable_world\<world_name>`만 Minecraft saves로 복사합니다.

## v1.1 월드 생성 원칙

- 월드 생성 입력은 accepted layer only입니다.
- suggested 후보만 있고 accepted feature가 없으면 월드 생성 버튼은 비활성 또는 오류 상태가 됩니다.
- Arnis Writer는 no-network 모드로 실행됩니다.
- Paper 26.1.2 load smoke를 통과한 월드만 release gate를 통과합니다.

## 키 저장 위치

```text
%APPDATA%\ArnisKorea\secrets.json
```

이 파일은 artifact와 프로젝트 폴더에 포함되지 않습니다.
