# Source Policy

Naver-only source policy는 외부 non-Naver 지도 데이터 사용 여부를 report에 명시합니다.

## Allowed

- `maps.apigw.ntruss.com`
- 공식 Static Map endpoint `/map-static/v2/raster`
- Dynamic Map은 bbox selector UI 용도
- Geocoding, Reverse Geocoding, Directions는 공식 Naver Cloud API로 구현할 때만 허용

## Blocked in Naver-only

- OSM, Overpass
- Overture
- AWS Terrain Tiles
- ESA WorldCover
- public/government geodata
- Naver internal map/tile endpoint
- unofficial scraping, browser capture, canvas extraction, traffic tampering

## Report fields

`source-policy-report.json`은 다음 값을 포함합니다.

```json
{
  "source_policy": "naver_only",
  "external_non_naver_sources_used": false,
  "official_naver_api_only": true,
  "renderer_no_network": true
}
```
