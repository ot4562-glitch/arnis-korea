# Windows Quickstart

## 1. Artifact 풀기

GitHub Actions artifact `arnis-korea-0.7.0-windows-x86_64` 안의 zip을 원하는 폴더에 풉니다.

## 2. GUI 실행

`arnis-korea.exe` 또는 `open-gui.bat`을 실행합니다. 기본 선택은 `Naver-only`, `지도형 모드`, `arnis-no-network` writer입니다.

## 3. Naver-only 생성

`네이버 API` 탭에 Maps Application Client ID/Client Secret을 저장합니다. `월드 생성` 탭에서 bbox, output folder, world name을 확인하고 Static Map 저장/분석 동의 후 `월드 생성`을 누릅니다.

v0.6.0 이하 prototype world는 Minecraft Java에서 열리지 않을 수 있습니다. v0.7.0 artifact는 Actions에서 Minecraft Java `1.21.1` headless load smoke를 통과해야 생성됩니다.

## 4. Minecraft saves로 복사

GUI의 `Minecraft saves로 복사`를 누릅니다. 이 버튼은 playable world folder만 복사합니다.

복사할 폴더:

```text
output-hufs-v07\world-hufs-naver-v07
```

복사하지 않을 폴더:

```text
output-hufs-v07\arnis_korea_project
```

## 5. CLI Smoke

```powershell
.\arnis-korea-cli.exe generate ^
  --source mock-naver ^
  --bbox "37.5955,127.0555,37.5985,127.0620" ^
  --output-dir ".\smoke-output" ^
  --world-name "world-load-smoke" ^
  --building-mode map-readable ^
  --terrain=false ^
  --interior=false ^
  --roof=true ^
  --writer arnis-no-network
```

성공 기준은 `level.dat` 존재가 아니라 Actions의 `minecraft_load_smoke.json`에서 `passed=true`입니다.
