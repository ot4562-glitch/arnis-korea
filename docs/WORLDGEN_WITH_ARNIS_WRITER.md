# Worldgen With Arnis Writer

v1.1부터 GUI에 `월드 생성` 탭이 추가됩니다.

## 입력

월드 생성 입력은 `accepted_layers.geojson`입니다. `suggested_layers.geojson`은 자동 후보 저장소일 뿐이며 사용자가 승인하지 않으면 worldgen에 들어가지 않습니다.

## 변환

`accepted_layers.geojson`은 `synthetic_osm.json`으로 변환됩니다.

- road LineString: `highway=residential`
- rail LineString: `railway=rail`
- building Polygon: `building=yes`, `building:levels=1~3`
- water Polygon: `natural=water`
- green Polygon: `leisure=park`
- spawn Point: OSM way로 넣지 않고 world spawn 옵션으로 전달

## Renderer

`dev-tools/arnis-korea-renderer.exe`는 patched Arnis no-network writer입니다.

```text
arnis-korea-renderer.exe --file synthetic_osm.json --bbox min_lat,min_lng,max_lat,max_lng --output-dir playable_world --terrain=false --interior=false --roof=true --scale 1.0
```

GUI와 QA는 Overpass, Overture, AWS Terrain Tiles, ESA WorldCover, Nominatim, update check를 worldgen 경로에서 사용하지 않는 것을 source policy report로 기록합니다.

## 출력

```text
project_dir/
  synthetic_osm.json
  reports/
    synthetic_osm_export_report.json
    source-policy-report.json
    worldgen-report.json
    minecraft-load-smoke.json
    world-validation.json
  playable_world/
    <world_name>/
```

Minecraft saves에는 `playable_world/<world_name>`만 복사합니다.
