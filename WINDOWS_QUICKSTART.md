# Windows Quickstart

## 1. Artifact 풀기

GitHub Actions artifact `arnis-korea-0.6.0-windows-x86_64` 안의 zip을 원하는 폴더에 풉니다.

## 2. GUI 실행

`arnis-korea.exe` 또는 `open-gui.bat`을 실행합니다. 기본 선택은 `Naver-only`와 `지도형 모드, 추천`입니다.

## 3. Naver-only 생성

`네이버 API` 탭에 Maps Application Client ID/Client Secret을 저장합니다. `월드 생성` 탭에서 bbox, output folder, world name을 확인하고 Static Map 저장/분석 동의 후 `먼저 미리보기 생성` 또는 `월드 생성`을 누릅니다.

`3D 건물 실험 모드`는 Static Map만으로 높이와 외관 정확도를 보장하지 않으므로 기본값이 아닙니다.

## 4. Minecraft saves로 복사

GUI의 `Minecraft saves로 복사`를 누릅니다. 이 버튼은 `output\<world_name>` 폴더만 복사합니다.

복사할 폴더:

```text
output-hufs-naver\world-hufs-naver
```

복사하지 않을 폴더:

```text
output-hufs-naver\arnis_korea_project
```

## 5. CLI smoke

```powershell
.\arnis-korea-cli.exe generate ^
  --source mock-naver ^
  --bbox "37.5955,127.0555,37.5985,127.0620" ^
  --output-dir ".\smoke-output" ^
  --world-name "world-readable-smoke" ^
  --building-mode map-readable ^
  --terrain=false ^
  --interior=false ^
  --roof=true ^
  --noise-filter-level high
```

성공 기준:

```text
smoke-output\world-readable-smoke\level.dat
smoke-output\world-readable-smoke\session.lock
smoke-output\world-readable-smoke\region\*.mca
smoke-output\arnis_korea_project\world_validation.json
smoke-output\arnis_korea_project\arnis-korea-quality-report.md
smoke-output\arnis_korea_project\debug\segmentation_preview.png
```

## 6. 품질 튜닝

도로가 약하면 `--road-width-multiplier`를 올립니다. 작은 조각이 많으면 `--noise-filter-level high`와 `--building-min-area`를 올립니다. 더 넓게 읽히는 지도가 필요하면 `--world-scale`을 올립니다.
