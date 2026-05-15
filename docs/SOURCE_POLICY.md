# Source Policy

v2.0.0 private-final source policy는 `naver_trace_editor_accepted_layers`입니다.

## 허용

- 공식 Naver Static Map API 배경
- Dynamic Map bbox selector UI 용도
- 사용자의 수동 trace
- 사용자가 명시적으로 승인한 suggested feature
- accepted layer 기반 synthetic OSM-like JSON
- patched Arnis no-network writer

## 차단

- 비공식 Naver scraping
- 네이버 지도 서비스의 내부 tile/vector 추출
- tile 좌표 추정, 브라우저 캡처, 개발자도구 로그/요청 가로채기
- Dynamic Map 내부 vector 추출
- OSM, Overpass, Overture, AWS Terrain Tiles, ESA WorldCover, Nominatim, public geodata 호출
- suggested layer를 사용자 승인 없이 worldgen 입력으로 사용

## Report

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
