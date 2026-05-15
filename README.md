# Arnis Korea private-final v2.0.0

Arnis Korea는 한국 지역을 Minecraft Java 월드로 만들기 위한 개인 개발용 Windows GUI입니다. 공개 배포용이 아니며, GitHub Actions artifact는 개인 Windows PC로 옮기기 위한 산출물입니다.

GUI 이름은 `Arnis Korea - 네이버 지도 월드 생성기`입니다. 일반 사용자는 root의 `arnis-korea.exe`만 실행합니다.

## 최종 지원 범위

- 네이버 공식 Static Map API 키 저장, 삭제, 테스트
- bbox/스폰포인트 설정과 Static Map 요청 계획 확인
- 네이버 Static Map 또는 mock 배경 위 수동 trace
- road, rail, building, water, green, spawn point 생성/선택/수정/삭제
- zoom, pan, point add/move/delete, undo/redo
- suggested 후보 보기, suggested -> accepted 승인, accepted -> suggested 되돌리기
- `accepted_layers.geojson`만 worldgen 입력으로 사용
- `accepted_layers.geojson` -> `synthetic_osm.json` export
- patched Arnis no-network writer로 `playable_world/<world_name>` 생성
- Paper 26.1.2 load smoke release gate
- Minecraft saves에는 playable world 폴더만 복사

## 하지 않는 것

- Static Map만으로 자동 3D 도시 복원
- suggested layer를 자동으로 worldgen에 사용
- 비공식 Naver scraping
- Naver 내부 tile/vector 추출
- OSM, Overpass, Overture, AWS Terrain Tiles, ESA WorldCover, Nominatim 호출
- 공개 GitHub Release 배포

품질은 사용자가 trace하고 승인한 accepted layer 품질에 의존합니다.

## Artifact

```text
arnis-korea-2.0.0-private-final-windows_x86_64
```

root:

```text
arnis-korea.exe
README.md
WINDOWS_QUICKSTART.md
NAVER_CLOUD_MAPS_KEY_GUIDE.md
docs/
examples/
open-gui.bat
```

`dev-tools/`에는 debug, CLI, renderer 실행 파일이 있을 수 있습니다. root에는 `arnis-korea-cli.exe`를 두지 않습니다.

## AI Trace Worker

AI Trace는 Windows EXE 내부 모델이 아니라 OCI 내부 worker 또는 dev-tools CLI로 실행합니다. GUI는 분석 패키지를 내보내고 결과를 suggested 후보로 가져옵니다. 사용자가 승인한 accepted layer만 월드 생성에 사용됩니다.
