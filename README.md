# Arnis Korea

한국 지도를 Minecraft Java 월드로 만들기 위한 Windows 데스크톱 앱입니다.

Arnis Korea는 upstream Arnis를 Windows 사용자가 바로 실행할 수 있도록 GUI, CLI, 지도 범위 선택, 네이버 Cloud Maps 연동 안내, 배포 패키지를 함께 제공합니다. 기본 월드 생성 경로는 OSM 데이터를 사용하며, Naver Static Map은 사용자가 직접 발급한 Maps Application 키와 명시적인 사용 조건 확인이 있을 때만 테스트합니다.

## 주요 기능

- `arnis-korea.exe`: 더블클릭으로 실행하는 Windows GUI
- `arnis-korea-cli.exe`: 고급 사용자와 문제 진단용 CLI
- 지도 bbox 입력, HUFS/서울 샘플, Dynamic Map selector 연결
- 스폰포인트 자동/수동 지정
- terrain, interior, roof, building-mode 옵션
- Naver Cloud Maps Client ID/Client Secret 저장 및 Static Map 단건 테스트
- upstream Arnis binary 동봉: `bin/arnis-upstream.exe`
- Windows 배포 zip 안에서 바로 실행 가능한 bat 파일 제공

## 화면

`docs/images/`에 제품 화면 이미지를 추가할 예정입니다. 현재 배포는 GUI 실행과 self-test를 우선 검증합니다.

## 빠른 시작

1. GitHub Actions artifact에서 `arnis-korea-0.2.0-windows-x86_64.zip`을 받습니다.
2. 원하는 폴더에 압축을 풉니다.
3. `arnis-korea.exe` 또는 `open-gui.bat`을 더블클릭합니다.
4. `월드 생성` 탭에서 bbox와 출력 폴더를 확인합니다.
5. `Generate World`를 누릅니다.
6. 생성된 월드 폴더를 `%APPDATA%\.minecraft\saves`로 복사합니다.

## Windows 설치

설치 프로그램은 아직 제공하지 않습니다. zip 압축 해제 방식입니다.

배포 zip 필수 파일:

```text
arnis-korea.exe
arnis-korea-cli.exe
bin/arnis-upstream.exe
README.md
WINDOWS_QUICKSTART.md
NAVER_CLOUD_MAPS_KEY_GUIDE.md
docs/
sample_bbox_hufs.json
config.example.yml
examples/mock_raster.ppm
web/dynamic_selector.html
open-gui.bat
run-help.bat
generate-hufs-osm.bat
plan-hufs-static.bat
```

## GUI 사용법

- `월드 생성`: 출력 폴더, bbox, 스폰포인트, terrain, 소스, 건물 옵션을 선택하고 월드를 생성합니다.
- `지도/범위`: bbox 직접 입력, 샘플 불러오기, Dynamic Map selector 열기, Static Map 요청 수 계산을 제공합니다.
- `네이버 API`: Maps Application의 Client ID/Client Secret을 저장하고 Static Map API를 단건 테스트합니다.
- `도구`: plan-static, mock-vectorize, CLI 명령 미리보기, 로그 저장을 제공합니다.
- `도움말`: Minecraft saves 폴더와 기본 사용 순서를 안내합니다.

## CLI 사용법

```powershell
.\arnis-korea-cli.exe help
.\arnis-korea-cli.exe version
.\arnis-korea-cli.exe plan-static --bbox-file ".\sample_bbox_hufs.json"
.\arnis-korea-cli.exe mock-vectorize --bbox-file ".\sample_bbox_hufs.json" --output-dir ".\outputs"
.\arnis-korea-cli.exe generate --bbox "37.5955,127.0555,37.5985,127.0620" --output-dir ".\world-hufs" --source osm --terrain --interior=false --roof=true
```

`building-mode`는 현재 MVP metadata로 기록됩니다.

```powershell
.\arnis-korea-cli.exe generate `
  --bbox "37.5955,127.0555,37.5985,127.0620" `
  --output-dir ".\world-hufs" `
  --source osm `
  --terrain `
  --spawn-lat 37.597 `
  --spawn-lng 127.059 `
  --interior=false `
  --roof=true `
  --building-mode campus-style
```

## Naver Maps 연동

공식 Static Map endpoint:

```text
https://maps.apigw.ntruss.com/map-static/v2/raster
```

앱에서 입력하는 값은 Ncloud 계정 Access Key가 아니라 Maps Application의 Client ID/Client Secret입니다. 자세한 절차는 [NAVER_CLOUD_MAPS_KEY_GUIDE.md](NAVER_CLOUD_MAPS_KEY_GUIDE.md)를 참고하세요.

Arnis Korea는 키를 exe에 포함하지 않습니다. GUI 저장 시 사용자 PC의 `%APPDATA%\ArnisKorea\secrets.json`에 저장하며, 이 파일은 배포물에 포함되지 않습니다.

## 라이선스와 주의사항

upstream Arnis는 Apache-2.0 프로젝트입니다. Arnis Korea의 자체 코드는 이 저장소의 라이선스를 따릅니다.

Naver Maps API 데이터는 Apache-2.0이 아닙니다. 이 배포물은 Naver 데이터 사용 권리를 제공하지 않으며, Naver 응답 이미지, cache, 파생 raster 데이터를 포함하지 않습니다. 사용자는 본인의 Naver Cloud Platform 계약과 Maps API 약관을 확인해야 합니다.

## 보안 정책

- GitHub token, Naver Client ID/Client Secret 원문을 저장소와 릴리스 zip에 포함하지 않습니다.
- GUI 로그에는 키 원문을 출력하지 않습니다.
- live Minecraft server world 경로, RCON, nginx, systemd 작업은 배포 과정에서 다루지 않습니다.
- 공식 Naver API 외의 지도 데이터 취득 방식은 사용하지 않습니다.

자세한 내용은 [docs/SECURITY.md](docs/SECURITY.md)를 참고하세요.

## Roadmap

- Windows GUI 안정화
- 지도 선택 UX 개선
- building-mode의 실제 geometry 반영
- 한국 공공데이터 adapter 검토
- 설치 프로그램 제공 검토

자세한 내용은 [docs/ROADMAP.md](docs/ROADMAP.md)를 참고하세요.

## Upstream Attribution

Arnis Korea는 Minecraft Java world generation을 위해 upstream Arnis binary를 호출합니다.

- upstream project: https://github.com/louis-e/arnis
- upstream license: Apache-2.0
