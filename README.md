# Arnis Korea v0.5 개인 개발판

Arnis Korea는 한국 지역을 Minecraft Java world로 만드는 개인 개발용 Windows 앱입니다. 이 저장소와 GitHub Actions artifact는 로컬 Windows PC로 private artifact를 옮기기 위한 개발 경로이며, 공개 배포용 릴리스나 홍보용 패키지가 아닙니다.

v0.5 기본 모드는 `Naver-only`입니다. 지도 소스는 공식 Naver Maps API만 사용하며, Arnis는 데이터 소스가 아니라 no-network world writer/renderer 경로로만 다룹니다.

## 핵심 정책

- Naver Static Map 공식 endpoint만 raster 입력으로 사용합니다.
- Dynamic Map은 bbox selector UI 용도입니다.
- OSM, Overpass, Overture, AWS Terrain Tiles, ESA WorldCover, 공공/공개 geodata는 Naver-only 모드에서 호출하지 않습니다.
- Naver 응답 이미지, cache, 파생 raster, API key, GitHub token은 repo/artifact에 포함하지 않습니다.
- Naver 지도 데이터 권리는 Apache-2.0이 아닙니다. 이 프로젝트는 개인 개발/실험용입니다.
- 네이버 내부 지도 데이터, 내부 tile URL, 브라우저 화면 캡처, canvas 추출, 트래픽 가로채기 방식은 사용하지 않습니다.

## Windows 빠른 시작

1. GitHub Actions artifact `arnis-korea-0.5.0-windows-x86_64`를 내려받습니다.
2. zip을 원하는 폴더에 풉니다.
3. `arnis-korea.exe` 또는 `open-gui.bat`을 실행합니다.
4. `네이버 API` 탭에서 Maps Application의 Client ID/Client Secret을 저장합니다.
5. `지도/범위` 탭에서 bbox와 Static Map 요청 수를 확인합니다.
6. `월드 생성` 탭에서 `Naver-only`를 선택하고 Static Map 저장/분석 동의를 체크합니다.
7. `Generate Naver-only World`를 누릅니다.

생성물은 선택한 output folder 안에만 저장됩니다. Minecraft Java에서는 생성된 world 폴더를 `%APPDATA%\.minecraft\saves` 아래로 옮긴 뒤 싱글플레이에서 엽니다.

## CLI 예시

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

API key 없이 smoke test를 하려면:

```powershell
.\arnis-korea-cli.exe generate --source mock-naver --bbox "37.5955,127.0555,37.5985,127.0620" --output-dir ".\world-hufs-naver-mock" --terrain=false --interior=false --roof=true --building-mode full
```

## 생성 파이프라인

1. bbox 입력
2. Static Map request plan 생성
3. 사용자 저장/분석 동의 확인
4. 공식 `/map-static/v2/raster` 호출
5. raster segmentation
6. feature cleanup/vectorize
7. `naver_synthetic_osm.json`, `naver_world_features.json` 생성
8. no-network minimal Java world writer 실행
9. `level.dat`, `region/*.mca`, quality report, source-policy report 생성

## 주요 파일

- `scripts/arnis_korea_gui.py`: Windows GUI
- `scripts/arnis_korea_detailed.py`: CLI
- `src/arnis_korea_detailed/source_policy.py`: Naver-only source guard/report
- `src/arnis_korea_detailed/naver_static_map_provider.py`: 공식 Static Map downloader
- `src/arnis_korea_detailed/naver_synthetic_layer.py`: Naver-derived synthetic layer
- `src/arnis_korea_detailed/minimal_world_writer.py`: no-network Java Anvil writer

## 제한

Static Map raster에서 건물 높이와 정확한 footprint를 알 수 없으므로 높이는 휴리스틱입니다. 지형은 기본 flat이며, Naver terrain raster estimate는 실험 모드입니다. 품질 한계는 [docs/QUALITY_LIMITS.md](docs/QUALITY_LIMITS.md)를 참고하세요.
