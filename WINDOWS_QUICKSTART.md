# Windows Quickstart

## 1. Artifact 풀기

GitHub Actions artifact `arnis-korea-0.5.2-windows-x86_64` 안의 zip을 원하는 폴더에 풉니다.

## 2. GUI 실행

`arnis-korea.exe` 또는 `open-gui.bat`을 실행합니다.

## 3. Naver-only 생성

`네이버 API` 탭에 Maps Application Client ID/Client Secret을 저장합니다. `월드 생성` 탭에서 bbox, output folder, world name을 확인하고 Static Map 저장/분석 동의 후 `월드 생성`을 누릅니다.

## 4. Minecraft saves로 복사

GUI의 `Minecraft saves로 복사`를 누릅니다. 이 버튼은 `output\<world_name>` 폴더만 복사합니다.

수동 복사 시에도 아래 폴더만 복사하세요.

```text
output-hufs-naver\world-hufs-naver
```

아래 폴더는 복사하지 않습니다.

```text
output-hufs-naver\arnis_korea_project
```

## 5. CLI smoke

```powershell
.\arnis-korea-cli.exe generate --source mock-naver --bbox "37.5955,127.0555,37.5985,127.0620" --output-dir ".\smoke-output" --world-name "world-hufs-naver-smoke" --terrain=false --interior=false --roof=true --building-mode full
```

성공 기준:

```text
smoke-output\world-hufs-naver-smoke\level.dat
smoke-output\world-hufs-naver-smoke\session.lock
smoke-output\world-hufs-naver-smoke\region\*.mca
smoke-output\arnis_korea_project\world_validation.json
```

## 6. v0.5.0 dirty folder repair

이 명령은 layout만 정리합니다. v0.5.0 minimal writer가 만든 invalid `level.dat`/`.mca`를 호환 world로 변환하지는 못합니다.

```powershell
.\arnis-korea-cli.exe repair-world-layout --input "%APPDATA%\.minecraft\saves\world-hufs-naver" --output "%APPDATA%\.minecraft\saves\world-hufs-naver-clean"
```
