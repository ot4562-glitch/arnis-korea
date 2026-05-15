# Arnis Korea v1.1.0 Arnis Writer Integration

Arnis Korea는 한국 지역을 Minecraft Java 월드로 만들기 위한 개인 개발용 Windows GUI입니다. GitHub Actions artifact는 개인 Windows PC로 옮기기 위한 산출물이며 공개 배포용 Release가 아닙니다.

GUI 이름은 `Arnis Korea - 네이버 지도 월드 생성기`입니다.

## v1.1에서 지원하는 것

- 한국어 Trace Editor GUI와 crash log, safe mode
- 네이버 공식 Static Map API 배경 표시와 수동 trace
- 도로, 건물, 수역, 녹지, 철도, 스폰포인트 생성/수정/삭제
- zoom, pan, feature 선택, 점 이동/삭제, undo/redo
- suggested 후보 보기와 사용자 승인
- accepted layer only export
- `accepted_layers.geojson` -> `synthetic_osm.json` 변환
- patched Arnis no-network writer를 통한 `playable_world/<world_name>` 생성
- Paper 26.1.2 호환 load smoke gate

## Source Policy

- 월드 생성 입력은 `accepted_layers.geojson`만 사용합니다.
- `suggested_layers.geojson`은 후보일 뿐이며 사용자가 승인하지 않으면 월드 생성에 들어가지 않습니다.
- 네이버 공식 API는 개인 개발자가 Naver Cloud에서 발급한 키와 무료 사용량 범위 안에서 직접 사용합니다.
- Arnis는 writer로만 사용하며 Overpass, Overture, AWS Terrain Tiles, ESA WorldCover, Nominatim 호출은 차단합니다.
- Naver key, GitHub token, generated raster, cache, debug output, generated world는 artifact에 포함하지 않습니다.

## 프로젝트 구조

```text
project_dir/
  project.arniskorea.json
  naver_raster/
  suggested_layers.geojson
  accepted_layers.geojson
  synthetic_osm.json
  reports/
  previews/
  playable_world/
    <world_name>/
```

Minecraft saves로 복사할 것은 `playable_world/<world_name>` 폴더뿐입니다. 프로젝트 파일, reports, naver_raster, previews, layer 파일은 복사하지 않습니다.

## Windows Artifact

```text
arnis-korea-1.1.0-windows_x86_64
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
```

개발용 실행 파일은 `dev-tools/` 아래에만 있습니다.

```text
dev-tools/arnis-korea-debug.exe
dev-tools/arnis-korea-cli.exe
dev-tools/arnis-korea-renderer.exe
```

root에는 `arnis-korea-cli.exe`를 노출하지 않습니다.
