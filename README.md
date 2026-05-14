# Arnis Korea v0.5.2 개인 개발판

Arnis Korea는 한국 지역을 Minecraft Java world로 만드는 개인 개발용 Windows 앱입니다. GitHub는 private artifact를 로컬 Windows PC로 옮기기 위한 개발 경로이며, 공개 Release 배포용이 아닙니다.

v0.5.2 기본 모드는 `Naver-only`입니다. 지도 입력은 공식 Naver Static Map raster에서 파생한 synthetic OSM-like local file이며, world writer는 patched upstream Arnis Java Anvil writer입니다. Arnis는 지도 데이터 소스로 쓰지 않고 no-network renderer로만 사용합니다.

## 중요

- v0.5.0의 `arnis_korea_minimal_anvil_writer` world는 Minecraft Java에서 열리지 않을 수 있습니다.
- v0.5.2부터 Naver-only 기본 writer는 `patched_arnis_no_network_renderer`입니다.
- Minecraft saves에 넣는 것은 `output_dir\<world_name>\` 폴더뿐입니다.
- `output_dir\arnis_korea_project\`는 raster, JSON, report가 들어가는 분석/디버그 폴더이며 saves에 복사하지 않습니다.

## 출력 구조

```text
output-hufs-naver/
  world-hufs-naver/
    level.dat
    session.lock
    region/
  arnis_korea_project/
    naver_raster/
    features.normalized.json
    naver_synthetic_osm.json
    naver_world_features.json
    source-policy-report.json
    arnis-korea-quality-report.md
    world_validation.json
```

## 정책

- Naver Static Map 공식 endpoint만 raster 입력으로 사용합니다.
- OSM, Overpass, Overture, AWS Terrain Tiles, ESA WorldCover, Nominatim, 공공/공개 geodata는 Naver-only 실행 경로에서 호출하지 않습니다.
- Naver 응답 이미지, cache, 파생 raster, API key, GitHub token은 repo/artifact에 포함하지 않습니다.
- 네이버 내부 지도 데이터, 내부 tile URL, 브라우저 화면 캡처, canvas 추출, 브라우저 개발자 도구나 트래픽 가로채기 방식은 사용하지 않습니다.
- Naver 지도 데이터 권리는 Apache-2.0이 아니며, 이 프로젝트는 개인 개발/실험용입니다.

## CLI

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

Mock smoke:

```powershell
.\arnis-korea-cli.exe generate --source mock-naver --bbox "37.5955,127.0555,37.5985,127.0620" --output-dir ".\smoke-output" --world-name "world-hufs-naver-smoke" --terrain=false --interior=false --roof=true --building-mode full
```

## GUI

GUI의 `Minecraft saves로 복사` 버튼은 playable world folder만 `%APPDATA%\.minecraft\saves`로 복사합니다. metadata 폴더는 복사하지 않습니다.
