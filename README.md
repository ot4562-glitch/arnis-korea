# Arnis Korea v0.7.0 개인 개발판

Arnis Korea는 한국 지역을 Minecraft Java world로 만드는 개인 개발용 Windows 앱입니다. GitHub는 private Actions artifact를 로컬 Windows PC로 옮기기 위한 경로이며, 공개 Release 배포용이 아닙니다.

v0.7.0은 compatibility-first rebuild입니다. v0.6.0은 map-readable pipeline prototype이었지만 사용자 Windows Minecraft Java에서 load compatibility 문제가 확인되었습니다. v0.7.0부터는 “파일 존재”가 아니라 headless Minecraft server load smoke가 릴리스 게이트입니다.

## Renderer

- 기본 writer: `--writer arnis-no-network`
- 기본 mode: `--building-mode map-readable`
- `custom-debug` writer는 릴리스 경로가 아니며 호환성 경고가 붙습니다.
- Actions는 Minecraft Java `1.21.1` server jar로 생성 월드를 실제 로드합니다.

## 출력 구조

```text
output-hufs-v07/
  world-hufs-naver-v07/
    level.dat
    session.lock
    region/
  arnis_korea_project/
    naver_raster/
    debug/
    features.normalized.json
    naver_synthetic_osm.json
    naver_world_features.json
    source-policy-report.json
    arnis-korea-quality-report.md
    world_validation.json
    minecraft_load_smoke.json
    logs/
```

Minecraft saves에 넣는 것은 `output_dir\<world_name>\` 폴더뿐입니다. `arnis_korea_project`는 분석/리포트 폴더이며 saves에 복사하지 않습니다.

## 정책

- Naver Static Map 공식 endpoint만 raster 입력으로 사용합니다.
- Naver-only 실행 경로에서 OSM, Overpass, Overture, AWS Terrain Tiles, ESA WorldCover, Nominatim, 공공/공개 geodata를 호출하지 않습니다.
- Naver 응답 이미지, cache, 파생 raster, API key, GitHub token은 repo/artifact에 포함하지 않습니다.
- 네이버 내부 지도 데이터, 내부 tile URL, 브라우저 화면 캡처, 개발자 도구나 트래픽 가로채기 방식은 사용하지 않습니다.

## Real Naver Command

```powershell
.\arnis-korea-cli.exe generate `
  --source naver-only `
  --bbox "37.5955,127.0555,37.5985,127.0620" `
  --output-dir ".\output-hufs-v07" `
  --world-name "world-hufs-naver-v07" `
  --building-mode map-readable `
  --terrain=false `
  --interior=false `
  --roof=true `
  --writer arnis-no-network `
  --allow-static-raster-storage `
  --allow-static-raster-analysis `
  --accept-naver-static-raster-terms
```

복사할 폴더:

```text
.\output-hufs-v07\world-hufs-naver-v07
```

복사하지 말 것:

```text
.\output-hufs-v07\arnis_korea_project
```

## Mock Load Smoke

```powershell
.\arnis-korea-cli.exe generate --source mock-naver --bbox "37.5955,127.0555,37.5985,127.0620" --output-dir ".\smoke-output" --world-name "world-load-smoke" --building-mode map-readable --terrain=false --interior=false --roof=true --writer arnis-no-network
```

Actions에서는 여기에 `--validate-minecraft-load --target-minecraft-version 1.21.1`을 추가해 실제 load smoke를 수행합니다.
