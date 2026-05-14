# Naver-only Mode

`naver-only`는 Arnis Korea v0.5의 기본 모드입니다. 공식 Naver Maps API로 얻은 Static Map raster만 지도 입력으로 사용합니다.

## CLI

```powershell
.\arnis-korea-cli.exe generate `
  --source naver-only `
  --bbox "37.5955,127.0555,37.5985,127.0620" `
  --output-dir ".\world-hufs-naver" `
  --terrain=false `
  --interior=false `
  --roof=true `
  --building-mode full `
  --allow-static-raster-storage `
  --allow-static-raster-analysis `
  --accept-naver-static-raster-terms
```

## Mock mode

`mock-naver`는 실제 Naver API key 없이 Actions와 로컬 smoke에서 같은 segmentation/synthetic/world writer 경로를 검증합니다.

## Output

- `features.normalized.json`
- `naver_synthetic_osm.json`
- `naver_world_features.json`
- `level.dat`
- `region/*.mca`
- `source-policy-report.json`
- `arnis-korea-quality-report.md`

Naver raster와 derived output은 local output folder 전용이며 GitHub artifact에 넣지 않습니다.
