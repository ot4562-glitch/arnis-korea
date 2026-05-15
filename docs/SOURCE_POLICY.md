# Source Policy

v1.1 source policy는 `naver_trace_editor_accepted_layers`입니다.

## 허용

- 공식 Naver Static Map API 배경
- 사용자의 수동 trace
- 사용자가 명시적으로 승인한 suggested feature
- accepted layer 기반 synthetic OSM-like JSON
- patched Arnis no-network writer

## 차단

- 비공식 Naver scraping
- Naver 내부 tile/vector 추출
- OSM, Overpass, Overture
- AWS Terrain Tiles, ESA WorldCover
- Nominatim 또는 public geodata 호출
- suggested layer를 사용자 승인 없이 worldgen 입력으로 사용

## Report

`reports/source-policy-report.json`은 다음 핵심 값을 기록합니다.

```json
{
  "source_policy": "naver_trace_editor_accepted_layers",
  "worldgen_input": "accepted_layers_only",
  "suggested_layers_used_for_worldgen": false,
  "external_non_naver_sources_used": false,
  "renderer_network_disabled": true,
  "synthetic_osm_used": true,
  "custom_anvil_writer_used": false
}
```
