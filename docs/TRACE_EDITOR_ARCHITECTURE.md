# Trace Editor Architecture

v0.9 구조는 GUI와 trace editor core를 분리합니다.

## Modules

- `scripts/arnis_korea_gui.py`: Windows 사용자용 Tkinter GUI
- `src/arnis_korea_detailed/trace_editor_core.py`: 프로젝트, layer, export, validation 로직
- `.github/workflows/release-arnis-korea.yml`: Windows artifact build와 QA

## Data Flow

1. 사용자가 프로젝트를 생성합니다.
2. bbox 기준으로 Static Map 요청 계획을 저장합니다.
3. 배경 raster는 사용자가 저장/분석에 동의한 경우에만 `naver_raster/` 아래에 둡니다.
4. 자동 후보는 `suggested_layers.geojson`에만 저장합니다.
5. 사용자 직접 trace 또는 사용자 승인을 거친 후보만 `accepted_layers.geojson`에 저장합니다.
6. export 단계에서 `synthetic_osm_preview.json`과 report를 생성합니다.

## Source Boundary

공식 Naver Static Map API와 사용자 입력만 v0.9 입력 경계입니다. Dynamic selector는 bbox 선택 보조 UI입니다.

월드 생성 writer는 v1.1에서 연결합니다.
