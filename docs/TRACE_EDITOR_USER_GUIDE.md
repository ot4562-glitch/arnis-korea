# Trace Editor User Guide

Arnis Korea v1.0은 네이버 지도 배경 위에 사용자가 직접 레이어를 만들고 편집하는 GUI입니다.

## 탭

- 프로젝트: 프로젝트 생성, 저장, 불러오기
- 네이버 API: Client ID/Secret 저장, 삭제, Static Map API 테스트
- 지도 범위: bbox, HUFS 샘플, 요청 계획, selector JSON import, 스폰포인트
- 레이어 편집: 도로, 건물, 수역, 녹지, 철도, 스폰포인트 feature 편집
- 내보내기: accepted layer와 synthetic preview export
- 검수/리포트: validation, source policy, project manifest 생성
- 도움말: v1.0 사용 흐름과 제한 안내

## Suggested와 Accepted

`suggested_layers.geojson`은 자동 후보입니다. 이 파일의 feature는 사용자가 승인하기 전까지 export 입력이 아닙니다.

`accepted_layers.geojson`은 사용자가 직접 그렸거나 suggested 후보를 명시적으로 승인한 feature만 포함합니다. v1.0 export와 v1.1 writer 연결의 입력은 accepted layer만 사용합니다.

## 앱이 열리지 않을 때

- `%APPDATA%\ArnisKorea\logs\latest.log`를 확인합니다.
- `arnis-korea.exe --safe-mode`로 빈 GUI 부팅을 확인합니다.
- `dev-tools\arnis-korea-debug.exe`를 실행하면 콘솔에서 traceback을 볼 수 있습니다.
- 오류 내용을 공유하기 전에 Naver 키 원문이 포함되어 있지 않은지 확인하세요.

## 레이어 타입

- `road`: LineString
- `building`: Polygon
- `water`: Polygon
- `green`: Polygon
- `rail`: LineString
- `spawn`: Point

## v1.0 제한

월드 생성은 지원하지 않습니다. `synthetic_osm_preview.json`은 다음 단계 연결을 위한 미리보기 파일입니다.
