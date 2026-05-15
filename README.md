# Arnis Korea v0.6.0 개인 개발판

Arnis Korea는 한국 지역을 Minecraft Java world로 만드는 개인 개발용 Windows 앱입니다. GitHub는 private Actions artifact를 로컬 Windows PC로 옮기기 위한 경로이며, 공개 Release 배포용이 아닙니다.

v0.6.0 기본 모드는 `Naver-only` + `map-readable`입니다. 목표는 3D 도시 자동복원이 아니라 도로, 수역, 녹지, 큰 건물 윤곽이 먼저 읽히는 지도형 Minecraft 월드입니다.

## 기본 렌더링

- 기본 `--building-mode map-readable`: 도로/녹지/수역 우선, 건물은 낮은 footprint/outline 중심
- `footprint-only`: 건물 바닥 윤곽만 표시
- `low-rise`: 건물을 2-5블록으로 낮게 표시
- `roads-green-water-only`: 건물 없이 도로/녹지/수역만 표시
- `full-experimental`: 기존 full extrusion 계열 실험 모드

Static Map만으로 실제 건물 높이와 정확한 입체 외관은 보장할 수 없습니다.

## 출력 구조

```text
output-hufs-naver/
  world-hufs-naver/
    level.dat
    session.lock
    region/
  arnis_korea_project/
    naver_raster/
    debug/
      original_static_map.png
      segmentation_preview.png
      class_mask_roads.png
      class_mask_buildings.png
      class_mask_green_water.png
      world_overlay_preview.png
    features.normalized.json
    naver_synthetic_osm.json
    naver_world_features.json
    source-policy-report.json
    arnis-korea-quality-report.md
    world_validation.json
```

Minecraft saves에 넣는 것은 `output_dir\<world_name>\` 폴더뿐입니다. `arnis_korea_project`와 raster/debug/cache 출력은 artifact나 saves에 포함하지 않습니다.

## 정책

- Naver Static Map 공식 endpoint만 raster 입력으로 사용합니다.
- Naver-only 실행 경로에서 OSM, Overpass, Overture, AWS Terrain Tiles, ESA WorldCover, Nominatim, 공공/공개 geodata를 호출하지 않습니다.
- Naver 응답 이미지, cache, 파생 raster, API key, GitHub token은 repo/artifact에 포함하지 않습니다.
- 네이버 내부 지도 데이터, 내부 tile URL, 브라우저 화면 캡처, canvas 추출, 브라우저 개발자 도구나 트래픽 가로채기 방식은 사용하지 않습니다.

## CLI

```powershell
.\arnis-korea-cli.exe generate `
  --source naver-only `
  --bbox "37.5955,127.0555,37.5985,127.0620" `
  --output-dir ".\output-hufs-naver" `
  --world-name "world-hufs-naver" `
  --terrain=false `
  --interior=false `
  --roof=true `
  --building-mode map-readable `
  --noise-filter-level high `
  --road-width-multiplier 1.5 `
  --allow-static-raster-storage `
  --allow-static-raster-analysis `
  --accept-naver-static-raster-terms
```

Mock smoke:

```powershell
.\arnis-korea-cli.exe generate --source mock-naver --bbox "37.5955,127.0555,37.5985,127.0620" --output-dir ".\smoke-output" --world-name "world-readable-smoke" --terrain=false --interior=false --roof=true --building-mode map-readable --noise-filter-level high
```

품질 튜닝 옵션은 `--noise-filter-level`, `--building-min-area`, `--road-width-multiplier`, `--building-mode`, `--world-scale`입니다.
