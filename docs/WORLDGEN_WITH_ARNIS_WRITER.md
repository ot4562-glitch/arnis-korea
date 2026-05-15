# Worldgen With Arnis Writer

private-final v2.0.0은 `accepted_layers.geojson`을 `synthetic_osm.json`으로 변환하고 patched Arnis no-network writer로 Minecraft Java world를 생성합니다.

## 입력 원칙

- worldgen 입력은 accepted layer only입니다.
- suggested layer는 후보이며 승인 전까지 사용하지 않습니다.
- spawn point는 synthetic OSM way로 넣지 않고 renderer spawn 옵션으로 전달합니다.

## Mapping

- road LineString: `highway=residential`, metadata에 따라 primary/secondary 가능
- rail LineString: `railway=rail`
- building Polygon: `building=yes`, `building:levels=1~3`
- water Polygon: `natural=water`
- green Polygon: `leisure=park`

## No-network renderer

Arnis는 writer로만 사용합니다. no-network path에서는 Overpass, Overture, AWS Terrain Tiles, ESA WorldCover, Nominatim, update check를 사용하지 않습니다.

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

Minecraft saves에는 `playable_world/<world_name>`만 복사합니다. reports, naver_raster, previews, project json, layer json은 복사하지 않습니다.
