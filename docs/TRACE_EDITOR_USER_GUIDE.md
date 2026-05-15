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

## 레이어 편집법

레이어 편집 탭에는 `그리기`, `선택`, `이동` 모드가 있습니다.

- 그리기: 레이어 종류를 고른 뒤 지도 위를 클릭해 점을 추가하고 `feature 저장`을 누릅니다.
- 선택: feature 또는 꼭짓점을 클릭합니다. 선택된 꼭짓점은 드래그해서 이동할 수 있습니다.
- 이동: 지도 배경을 드래그해 pan 합니다.
- 마우스 휠 또는 `+`, `-`, `Reset` 버튼으로 zoom을 조정합니다.
- `선택 점 삭제`는 선택된 polyline/polygon 꼭짓점을 삭제합니다.
- `선택 feature 삭제`는 accepted feature를 삭제합니다.
- `Undo`, `Redo`는 accepted layer 편집 이력을 되돌리거나 다시 적용합니다.
- `이름/메모/class 적용`은 선택 feature의 레이어 class, 이름, 메모를 저장합니다.
- `accepted를 suggested로`는 선택된 accepted feature를 export 입력에서 빼고 suggested 후보로 되돌립니다.

도형 저장 시 canvas pixel 좌표는 bbox 기준 lat/lng GeoJSON geometry로 변환됩니다. Polygon은 저장 시 닫힌 ring으로 저장됩니다.

## 검수와 내보내기

- `accepted_layers.geojson export`: accepted layer만 저장합니다.
- `synthetic_osm_preview.json export`: v1.1 writer 연결 전 미리보기 파일을 생성합니다.
- `layer_validation_report.json 생성`: schema, 닫힌 polygon, road/rail line, duplicate id, 좌표 round-trip을 검사합니다.

자동 후보는 계속 `suggested_layers.geojson`에만 남습니다. 사용자가 승인하지 않은 suggested feature는 accepted layer와 export 입력으로 들어가지 않습니다.

## v1.0 제한

월드 생성은 지원하지 않습니다. `synthetic_osm_preview.json`은 다음 단계 연결을 위한 미리보기 파일입니다.
