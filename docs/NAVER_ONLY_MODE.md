# Naver-only Mode

v0.7.0 Naver-only mode는 공식 Naver Static Map raster를 분석해 synthetic OSM-like local file을 만들고, patched Arnis no-network renderer에 `--file`로 전달합니다.

## Compatibility Gate

v0.7.0부터 Minecraft load smoke가 필수입니다. `level.dat`, `session.lock`, `region/*.mca` 존재만으로는 PASS가 아닙니다.

Actions는 임시 Minecraft Java `1.21.1` server directory를 만들고 생성 world를 `world` 폴더로 복사한 뒤 server jar를 `nogui`로 실행합니다. `Done` 로그, crash report 부재, level/region/chunk fatal 오류 부재를 확인합니다.

## Renderer

- 기본 writer: `arnis-no-network`
- custom writer: `custom-debug`, 릴리스 차단 경로
- `--terrain=false`, `--land-cover=false`, `--file naver_synthetic_osm.json`
- renderer network disabled

## Synthetic OSM

`naver_synthetic_osm.json`은 다음 sanity check를 통과해야 합니다.

- unique node/way ids
- all way node refs exist
- building/water/green polygons closed
- coordinates clipped to bbox
- tags compatible with Arnis parser: `building=yes`, `highway=*`, `natural=water`, `leisure=park`, `railway=rail`

## Output

- playable world: `<output_dir>\<world_name>\`
- project metadata: `<output_dir>\arnis_korea_project\`
- compatibility report: `<output_dir>\arnis_korea_project\minecraft_load_smoke.json`

Naver-only mode does not call OSM, Overpass, Overture, AWS, ESA, Nominatim, or public geodata sources.
