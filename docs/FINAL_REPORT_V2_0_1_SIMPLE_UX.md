# Arnis Korea v2.0.1 Simple UX Final Report

## Release refs

- Commit: run `git rev-parse HEAD` in the release workspace
- Tag: `arnis-korea-v2.0.1-simple-ux`
- Artifact name: `arnis-korea-2.0.1-simple-ux-windows_x86_64`
- Actions run URL: blocked until authenticated push
- Artifact id: blocked until Windows Actions completes
- Artifact SHA256: blocked until Windows Actions completes

## Current remote blocker

The local release branch is ahead of `origin/main`, but this environment has no GitHub HTTPS credentials or SSH key.

```text
git push origin main arnis-korea-v2.0.1-simple-ux
fatal: could not read Username for 'https://github.com': No such device or address
```

Public GitHub API currently shows:

- remote `main`: `a80b05200b4587ec13454c26faece530e8f038c9`
- latest workflow run: `25917916181`, `arnis-korea-v2.0.0-private-final`, success
- latest artifact: `7017231404`, `arnis-korea-2.0.0-private-final-windows_x86_64`
- missing remote tag/artifact: `arnis-korea-v2.0.1-simple-ux`, `arnis-korea-2.0.1-simple-ux-windows_x86_64`

## Simplified screen structure

Default beginner mode shows a three-step wizard only:

1. `시작하기`
   - 새 지도 만들기
   - 기존 프로젝트 열기
   - 최근 프로젝트
   - 도움말
   - 네이버 API 키 상태: 설정됨 / 미설정 / 테스트 필요
   - API 키 설정
2. `지도 만들기`
   - 위치/범위 선택
   - 네이버 지도 불러오기
   - AI 후보 생성
   - 레이어 확인/수정
   - 승인된 레이어 수: 도로 / 건물 / 녹지 / 수역 / 철도
   - 다음: 월드 생성
3. `마인크래프트로 내보내기`
   - 지도 범위 확인
   - 승인된 레이어 확인
   - 월드 이름 입력
   - 월드 생성
   - Minecraft saves로 복사
   - 생성된 월드 폴더 열기
   - 게임에서 여는 방법 보기

Bottom beginner buttons:

- `문제 해결`
- `로그`

Full advanced mode opens only through `고급 설정 열기`.

## Hidden advanced menu list

These are hidden from the default screen and remain available through advanced settings or troubleshooting:

- confidence threshold
- source-policy-report / 데이터 사용 안전 검사
- synthetic_osm.json / 월드 생성용 변환 데이터
- accepted_layers.geojson direct export
- suggested_layers.geojson
- Paper 26.1.2 compatibility check
- renderer / 월드 생성 엔진
- dev CLI
- AI worker package export/import
- debug preview
- logs and reports

## Preserved functions

- 프로젝트 생성/열기/저장
- 네이버 API 키 저장/삭제/테스트
- Static Map 배경 다운로드
- AI 후보 생성
- 승인된 레이어 관리
- 레이어 편집
- 월드 생성
- Minecraft saves 복사
- dev-tools internal CLI/debug/renderer/AI worker packaging

## Local verification

PASS locally:

```text
python -m py_compile scripts/arnis_korea_gui.py
xvfb-run -a python scripts/arnis_korea_gui.py --self-test-gui
xvfb-run -a python scripts/arnis_korea_gui.py --safe-mode --self-test-gui
xvfb-run -a python scripts/arnis_korea_gui.py --self-test-simple-wizard
xvfb-run -a python scripts/arnis_korea_gui.py --self-test-beginner-flow
xvfb-run -a python scripts/arnis_korea_gui.py --self-test-advanced-mode
PYTHONPATH=src python -m arnis_korea_detailed.trace_editor_core self-test
PYTHONPATH=src python -m arnis_korea_detailed.trace_worldgen self-test
PYTHONPATH=src python -m arnis_korea_detailed.trace_worldgen final-qa --output-dir /tmp/arnis-v201-finalqa-no-renderer --root .
python scripts/release_scan.py .
git diff --check
```

## Windows test procedure

After pushing the tag from an authenticated environment, confirm the workflow run for `arnis-korea-v2.0.1-simple-ux` passes these gates:

1. Packaged `arnis-korea.exe --self-test-gui`
2. Packaged `arnis-korea.exe --safe-mode --self-test-gui`
3. Packaged `arnis-korea.exe --self-test-simple-wizard`
4. Packaged `arnis-korea.exe --self-test-beginner-flow`
5. Packaged `arnis-korea.exe --self-test-advanced-mode`
6. Packaged `dev-tools\arnis-korea-debug.exe --self-test-gui`
7. `%APPDATA%\ArnisKorea\logs\latest.log` creation
8. Mock project -> AI 후보 -> 승인 -> 월드 생성 -> Minecraft saves copy simulation
9. Existing v2.0 QA gates
10. Source/package secret, raster, world, cache scans
11. Artifact root exposes only `arnis-korea.exe`

After the run succeeds, record:

- Actions run URL
- artifact id
- artifact name
- SHA256 from `SHA256SUMS.windows`
- `MANIFEST.windows.txt`
