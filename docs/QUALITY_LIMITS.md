# Quality Limits

Static Map raster는 화면 표현용 이미지입니다. v0.7.0의 첫 목표는 Minecraft load compatibility입니다. 품질 튜닝은 headless load smoke가 통과한 뒤에만 의미가 있습니다.

리포트에 기록되는 핵심 한계:

- `height_source=heuristic_from_naver_raster`
- `exact_height_available=false`
- `terrain_source=flat` 기본값
- `external_dem_used=false`
- 건물 footprint는 raster segmentation 기반 후보입니다.
- 도로, 수역, 녹지, 철도는 색상 profile과 connected component 기반 추정입니다.
- Static Map label/icon noise는 필터링하지만 완전히 제거된다고 보장하지 않습니다.
- v0.6.0 이하 prototype world는 Minecraft Java에서 열리지 않을 수 있습니다.

품질 튜닝:

- `--noise-filter-level high`: 작은 label/icon/noise 후보를 강하게 제거
- `--building-min-area`: 작은 건물 조각 제거 기준 상향
- `--road-width-multiplier`: 도로 가독성 확대
- `--building-mode`: 기본은 `map-readable`, 입체 건물은 `full-experimental`
- `--world-scale`: Minecraft world에서 같은 bbox를 더 크게 표현

처음에는 작은 bbox로 테스트하는 것을 권장합니다. 너무 넓은 bbox는 feature가 많아지고, 너무 좁은 bbox는 도로/건물 경계가 뭉개질 수 있습니다.
