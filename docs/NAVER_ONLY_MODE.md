# Naver-only Mode

v0.5.2 Naver-only mode는 공식 Naver Static Map raster를 분석해 synthetic OSM-like local file을 만들고, patched Arnis no-network renderer에 `--file`로 전달합니다.

## Renderer

- 기본 writer: `patched_arnis_no_network_renderer`
- fallback/debug only: `arnis_korea_minimal_anvil_writer`
- target Minecraft Java: 1.21.x
- `--file` 없는 renderer 실행은 실패합니다.
- Overture, Overpass, elevation external fetch, land-cover external fetch, Nominatim은 Naver-only renderer path에서 비활성화됩니다.

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
  --building-mode full `
  --allow-static-raster-storage `
  --allow-static-raster-analysis `
  --accept-naver-static-raster-terms
```

Minecraft saves에 복사할 폴더:

```text
.\output-hufs-naver\world-hufs-naver
```

복사하지 말 것:

```text
.\output-hufs-naver\arnis_korea_project
```

## Output

- playable world: `<output_dir>\<world_name>\`
- project metadata: `<output_dir>\arnis_korea_project\`

`world_validation.json`은 metadata 폴더에 저장됩니다.
