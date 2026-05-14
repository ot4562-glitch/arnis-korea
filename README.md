# Arnis Korea

Arnis Korea packages upstream Arnis with Korean map-generation UX: bbox
selection, official Naver Static Map request planning, guarded Static Map
probing, mock raster vectorization, and Korea-oriented feature/style metadata.

The default world-generation path is still OSM-first and delegates Minecraft
Java world output to a bundled or locally built upstream Arnis binary.

## Windows Usage

```powershell
.\arnis-korea.exe help
.\arnis-korea.exe version
.\arnis-korea.exe plan-static --bbox-file ".\sample_bbox_hufs.json"
.\arnis-korea.exe mock-vectorize --bbox-file ".\sample_bbox_hufs.json" --output-dir ".\outputs"
.\arnis-korea.exe generate --bbox "37.5955,127.0555,37.5985,127.0620" --output-dir ".\world-hufs" --source osm --terrain
```

Naver keys are never bundled. Provide your own key by environment variable:

```powershell
$env:NAVER_MAPS_API_KEY_ID="your-key-id"
$env:NAVER_MAPS_API_KEY="your-key"
.\arnis-korea.exe probe-naver --bbox-file ".\sample_bbox_hufs.json"
```

Or by local files:

```powershell
.\arnis-korea.exe probe-naver `
  --bbox-file ".\sample_bbox_hufs.json" `
  --naver-key-id-file ".\secrets\naver_key_id.txt" `
  --naver-key-file ".\secrets\naver_key.txt"
```

## Linux Usage

```bash
./arnis-korea generate \
  --bbox "37.5955,127.0555,37.5985,127.0620" \
  --output-dir ./world-hufs \
  --source osm \
  --terrain
```

## Official Naver Static Map Provider

Only this official endpoint is used:

```text
https://maps.apigw.ntruss.com/map-static/v2/raster
```

Authentication headers:

```text
x-ncp-apigw-api-key-id
x-ncp-apigw-api-key
```

Default request parameters are `crs=EPSG:4326`, `w=1024`, `h=1024`,
`level=16`, `format=png`, `scale=2`, `maptype=basic`, and `lang=ko`.

Planning does not call Naver:

```powershell
.\arnis-korea.exe plan-static --bbox-file ".\sample_bbox_hufs.json"
```

`probe-naver` performs one request and prints status, content type, byte count,
and SHA-256 prefix. It does not save the image.

Static image download is blocked unless all gates are explicit:

```powershell
.\arnis-korea.exe download-static `
  --bbox-file ".\sample_bbox_hufs.json" `
  --output-dir ".\outputs" `
  --naver-key-id-file ".\secrets\naver_key_id.txt" `
  --naver-key-file ".\secrets\naver_key.txt" `
  --allow-static-raster-storage `
  --allow-static-raster-analysis `
  --accept-naver-static-raster-terms
```

## Dynamic Map Selector

Open `web/dynamic_selector.html` locally and replace
`YOUR_NAVER_MAPS_DYNAMIC_CLIENT_ID` with your own Dynamic Map client ID for
local operator use. The selector only exports bbox JSON compatible with
Arnis Korea.

## Korea Advantages Over Raw Arnis

- Korea style profiles: apartment, villa, shop, school, office, campus,
  landmark, generic.
- Building height source design: OSM building levels, OSM height, public
  building future adapter, DEM/DSM future adapter, heuristic fallback.
- Static raster segmentation pipeline: mock raster today; real Naver raster
  requires explicit storage, analysis, and terms gates.
- Normalized feature JSON for road, building, water, green, rail, and terrain
  metadata.
- Feature fusion design for OSM base, Naver Static hints, Korean public data,
  and future DEM adapters.
- Minecraft palette notes for Korean apartments, campuses, shop streets,
  roads, sidewalks, rail, water, and green spaces.

## Licensing

Upstream Arnis is Apache-2.0. Naver Maps API data is not Apache-2.0, and this
distribution does not grant Naver data rights. Operators must provide their own
Naver credentials and comply with the applicable Naver terms before storing or
analyzing Static Map raster data.

The release does not include Naver API keys, Naver response images, Naver
caches, or Naver-derived raster data.
