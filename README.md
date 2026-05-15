# Arnis Korea v0.9.0 Trace Editor MVP

Arnis Korea는 한국 지역을 Minecraft 월드로 만들기 위한 개인 개발용 Windows GUI입니다. 이 저장소의 GitHub Actions artifact는 개인 Windows PC로 옮기기 위한 산출물이며 공개 배포용 Release가 아닙니다.

v0.9.0의 목표는 월드 생성 품질 개선이 아닙니다. 이번 버전은 **Naver Trace Editor + Arnis Writer** 방향의 첫 MVP이며, 사용자가 네이버 지도 배경 위에 레이어를 직접 만들고 저장/불러오기/내보내기 할 수 있게 하는 데 집중합니다.

GUI 이름은 `Arnis Korea - 네이버 지도 월드 생성기`입니다.

## v0.9에서 지원하는 것

- 프로젝트 생성/저장/불러오기
- 네이버 Static Map API 키 저장, 삭제, 연결 테스트
- bbox 직접 입력, HUFS 샘플 bbox, 요청 계획 표시
- Dynamic selector HTML을 bbox 선택 보조 UI로 열기
- 도로, 건물, 수역, 녹지, 철도, 스폰포인트 레이어 편집
- suggested layer 보기와 사용자 승인
- accepted layer만 export 입력으로 사용
- `accepted_layers.geojson` export
- `synthetic_osm_preview.json` export
- source policy report와 trace editor validation report 생성

## v0.9에서 하지 않는 것

- Minecraft 월드 생성
- Arnis Writer 연결
- 자동 후보를 사용자 승인 없이 accepted layer에 넣기
- 비공식 scraping
- Naver 내부 지도 데이터 접근
- 외부 공개 지리 데이터 호출

월드 생성 연결은 v1.1 목표입니다. GUI에도 다음 문구를 명확히 표시합니다.

```text
v0.9에서는 레이어 편집과 내보내기까지 지원합니다. Minecraft 월드 생성은 v1.1에서 Arnis Writer와 연결됩니다.
```

## 프로젝트 구조

```text
project_dir/
  project.arniskorea.json
  naver_raster/
  suggested_layers.geojson
  accepted_layers.geojson
  synthetic_osm_preview.json
  reports/
  previews/
```

`project.arniskorea.json`에는 schema version, project name, bbox, spawn point, Static Map 요청 계획, raster 파일 목록, layer 경로, 생성/수정 시각, source policy가 들어갑니다.

## Source Policy

- 공식 Naver Static Map API를 배경 raster 입력으로 사용할 수 있습니다.
- Dynamic Map은 bbox 선택용 외부 HTML 보조 UI로만 사용합니다.
- Geocoding/Reverse Geocoding은 선택적 주소 검색 보조로만 다룹니다.
- 사용자 수동 trace와 사용자가 승인한 suggested feature만 accepted layer가 됩니다.
- Naver key, GitHub token, 저장된 raster, cache, debug output, world output은 artifact에 포함하지 않습니다.

## Windows Artifact

Actions artifact 이름:

```text
arnis-korea-0.9.0-windows_x86_64
```

artifact root:

```text
arnis-korea.exe
README.md
WINDOWS_QUICKSTART.md
NAVER_CLOUD_MAPS_KEY_GUIDE.md
docs/
examples/
open-gui.bat
dev-tools/arnis-korea-cli.exe
```

root에는 `arnis-korea-cli.exe`를 노출하지 않습니다.
