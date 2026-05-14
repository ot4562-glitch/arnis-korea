# Windows Quickstart

## 1. Artifact 풀기

GitHub Actions artifact `arnis-korea-0.5.0-windows-x86_64` 안의 zip을 원하는 폴더에 풉니다. 이 artifact는 개인 개발용입니다.

## 2. GUI 실행

`arnis-korea.exe` 또는 `open-gui.bat`을 더블클릭합니다.

## 3. 네이버 키 저장

GUI의 `네이버 API` 탭에 Naver Cloud Maps Application의 Client ID/Client Secret을 붙여넣고 저장합니다. 키는 `%APPDATA%\ArnisKorea\secrets.json`에만 저장되며 artifact에 포함되지 않습니다.

## 4. Naver-only world 생성

`월드 생성` 탭에서 기본값 `Naver-only`를 사용합니다. Static Map 저장/분석 동의와 공식 조건 확인을 체크한 뒤 `Generate Naver-only World`를 누릅니다.

기본 HUFS 테스트 bbox:

```text
37.5955,127.0555,37.5985,127.0620
```

## 5. Mock smoke

실제 Naver API 없이 writer만 확인하려면:

```powershell
.\arnis-korea-cli.exe generate --source mock-naver --bbox "37.5955,127.0555,37.5985,127.0620" --output-dir ".\world-hufs-naver-mock" --terrain=false --interior=false --roof=true --building-mode full
```

성공하면 `level.dat`, `region\r.0.0.mca`, `source-policy-report.json`, `arnis-korea-quality-report.md`가 생성됩니다.

## 6. Minecraft에서 열기

생성된 world 폴더를 아래 경로로 옮깁니다.

```text
%APPDATA%\.minecraft\saves
```

Minecraft Java Edition을 실행하고 싱글플레이 월드 목록에서 선택합니다.
