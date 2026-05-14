# Windows Quickstart

## 1. 압축 풀기

`arnis-korea-0.2.0-windows-x86_64.zip`을 원하는 폴더에 풉니다.

## 2. GUI 실행

`arnis-korea.exe` 또는 `open-gui.bat`을 더블클릭합니다.

## 3. HUFS 샘플 생성

기본 bbox는 HUFS 인근의 작은 테스트 범위입니다.

```text
37.5955,127.0555,37.5985,127.0620
```

`월드 생성` 탭에서 `Generate World`를 누르면 `world-hufs` 폴더가 생성됩니다.

## 4. Minecraft에 넣기

생성된 world 폴더를 아래 폴더로 복사합니다.

```text
%APPDATA%\.minecraft\saves
```

Minecraft Java Edition을 실행한 뒤 싱글플레이 월드 목록에서 선택합니다.

## 5. CLI 확인

```powershell
.\arnis-korea-cli.exe help
.\arnis-korea-cli.exe version
.\arnis-korea-cli.exe generate --bbox "37.5955,127.0555,37.5985,127.0620" --output-dir ".\world-hufs" --source osm --terrain --interior=false --roof=true
```

## 6. 네이버 API 테스트

Naver Cloud Platform Console에서 Maps Application의 Client ID/Client Secret을 확인한 뒤 GUI의 `네이버 API` 탭에 붙여넣고 저장합니다. `Static Map API 테스트` 결과가 `200`과 `image/png`이면 정상입니다.
