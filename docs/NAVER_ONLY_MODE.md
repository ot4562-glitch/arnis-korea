# Naver-only Mode

v0.6.0 Naver-only mode는 공식 Naver Static Map raster를 분석해 로컬 synthetic feature layer를 만들고, 기본적으로 지도형 Minecraft world writer로 낮고 읽기 쉬운 월드를 생성합니다.

## Renderer

- 기본 writer: `arnis_korea_minimal_anvil_writer` map-readable path
- 실험 writer: `full-experimental` 또는 `--writer arnis`에서 patched Arnis no-network renderer 사용
- target Minecraft Java: 1.21.x
- renderer network는 Naver-only path에서 비활성화됩니다.
- Overture, Overpass, elevation external fetch, land-cover external fetch, Nominatim은 Naver-only path에서 비활성화됩니다.

## Building Modes

- `map-readable`: 기본값, 도로/녹지/수역 우선, 건물 1-3블록 footprint/outline 중심
- `footprint-only`: 건물 바닥 윤곽만
- `low-rise`: 낮은 건물 2-5블록
- `roads-green-water-only`: 건물 생성 안 함
- `full-experimental`: 기존 full building extrusion 실험 옵션

## Real Naver command

```powershell
.\arnis-korea-cli.exe generate `
  --source naver-only `
  --bbox "37.5955,127.0555,37.5985,127.0620" `
  --output-dir ".\output-hufs-naver" `
  --world-name "world-hufs-naver" `
  --terrain=false `
  --interior=false `
  --roof=true `
  --building-mode map-readable `
  --noise-filter-level high `
  --road-width-multiplier 1.5 `
  --allow-static-raster-storage `
  --allow-static-raster-analysis `
  --accept-naver-static-raster-terms
```

## Output

- playable world: `<output_dir>\<world_name>\`
- project metadata: `<output_dir>\arnis_korea_project\`
- debug previews: `<output_dir>\arnis_korea_project\debug\`

`features.normalized.json`에는 class별 count, before/after filter count, dropped noise count가 기록됩니다.
