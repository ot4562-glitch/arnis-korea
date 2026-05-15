# Layer Schema

Layer 파일은 GeoJSON FeatureCollection입니다.

```json
{
  "type": "FeatureCollection",
  "schema_version": "arnis-korea.trace-layer.v1.0",
  "features": []
}
```

## Properties

```json
{
  "id": "ak-...",
  "layer": "road",
  "name": "",
  "memo": "",
  "source": "user_approved",
  "approved_by_user": true,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

Suggested feature는 다음 값을 사용합니다.

```json
{
  "source": "static_map_color_candidate",
  "approved_by_user": false,
  "confidence": 0.4
}
```

Accepted feature는 `approved_by_user: true`여야 합니다.

## Geometry

- road: `LineString`
- building: `Polygon`
- water: `Polygon`
- green: `Polygon`
- rail: `LineString`
- spawn: `Point`
