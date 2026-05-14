# Quality Limits

Static Map raster는 화면 표현용 이미지입니다. 따라서 v0.5 Naver-only 결과는 다음 한계를 report에 기록합니다.

- `height_source=heuristic_from_naver_raster`
- `exact_height_available=false`
- `terrain_source=flat` 기본값
- `external_dem_used=false`
- 건물 footprint는 raster segmentation 기반 후보입니다.
- 도로, 수역, 녹지, 철도는 색상 profile과 connected component 기반 추정입니다.
- label/icon noise는 작은 object 제거와 confidence score로 완화합니다.

작은 bbox부터 테스트하는 것을 권장합니다. 큰 bbox는 Static Map 요청 수와 raster segmentation 시간이 증가합니다.
