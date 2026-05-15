# Trace Editor User Guide

Arnis Korea v1.1은 네이버 지도 배경 위에 사용자가 직접 레이어를 만들고, 승인된 accepted layer만으로 Minecraft Java 월드를 생성하는 GUI입니다.

## 탭

- 프로젝트: 프로젝트 생성, 저장, 불러오기
- 네이버 API: Client ID/Secret 저장, 삭제, Static Map API 테스트
- 지도 범위: bbox, HUFS 샘플, 요청 계획, selector JSON import, 스폰포인트
- 레이어 편집: 도로, 건물, 수역, 녹지, 철도, 스폰포인트 편집
- 내보내기: accepted layer, synthetic OSM, validation report 생성
- 월드 생성: Arnis Writer no-network worldgen 실행
- 검수/리포트: validation, source policy, project manifest 확인
- 도움말: 사용 흐름과 로그 위치

## Suggested와 Accepted

`suggested_layers.geojson`은 자동 후보입니다. 사용자가 승인하기 전까지 export와 worldgen 입력이 아닙니다.

`accepted_layers.geojson`은 사용자가 직접 그렸거나 suggested 후보를 명시적으로 승인한 feature만 포함합니다. v1.1 월드 생성은 accepted layer만 사용합니다.

## 레이어 편집법

- 그리기: 레이어 종류를 고른 뒤 지도 위를 클릭해 점을 추가하고 `feature 저장`을 누릅니다.
- 선택: feature 또는 꼭짓점을 클릭합니다. 선택된 꼭짓점은 드래그해서 이동할 수 있습니다.
- 이동: 지도 배경을 드래그해 pan 합니다.
- 마우스 휠 또는 `+`, `-`, `Reset` 버튼으로 zoom을 조정합니다.
- `선택 점 삭제`는 선택된 polyline/polygon 꼭짓점을 삭제합니다.
- `선택 feature 삭제`는 accepted feature를 삭제합니다.
- `Undo`, `Redo`는 accepted layer 편집 이력을 되돌리거나 다시 적용합니다.
- `accepted를 suggested로`는 선택된 accepted feature를 worldgen 입력에서 빼고 suggested 후보로 되돌립니다.

도형 저장 시 canvas pixel 좌표는 bbox 기준 lat/lng GeoJSON geometry로 변환됩니다. Polygon은 닫힌 ring으로 저장됩니다.

## 월드 생성

1. accepted feature가 있는지 확인합니다.
2. `내보내기` 탭에서 `synthetic_osm.json export`를 실행하거나, `월드 생성` 탭에서 바로 생성합니다.
3. 월드 이름과 scale, roof/interior 옵션을 확인합니다.
4. `월드 생성`을 누릅니다.
5. 생성 결과는 `project_dir/playable_world/<world_name>`에 저장됩니다.

Minecraft saves에는 `playable_world/<world_name>`만 복사합니다. 프로젝트 파일, reports, naver_raster, previews, layer 파일은 복사하지 않습니다.

## v1.1 제한

- 건물 높이는 footprint 또는 low-rise 중심입니다.
- terrain estimate는 기본 비활성입니다.
- GUI에서 생성한 월드는 release QA에서 Paper 26.1.2 load smoke를 통과해야 성공으로 봅니다.
