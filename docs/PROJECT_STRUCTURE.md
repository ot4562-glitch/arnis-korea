# Project Structure

```text
project_dir/
  project.arniskorea.json
  naver_raster/
  suggested_layers.geojson
  accepted_layers.geojson
  synthetic_osm_preview.json
  synthetic_osm.json
  reports/
  previews/
  playable_world/
    <world_name>/
```

`naver_raster/`는 사용자가 저장/분석에 동의한 Static Map 배경만 저장합니다.

`accepted_layers.geojson`은 worldgen 입력입니다. `suggested_layers.geojson`은 후보이며 승인 전까지 입력이 아닙니다.

`playable_world/<world_name>`만 Minecraft saves로 복사합니다.
