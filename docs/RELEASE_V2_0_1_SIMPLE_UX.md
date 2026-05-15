# Arnis Korea v2.0.1 Simple UX Release Handoff

## Release refs

- Commit: run `git log -1 --oneline --decorate` in the release workspace
- Tag: `arnis-korea-v2.0.1-simple-ux`
- Artifact name: `arnis-korea-2.0.1-simple-ux-windows_x86_64`

If this commit was received as a bundle, verify it first:

```bash
git bundle verify /root/MINSEONG_CODEX_OPERATION/artifacts/arnis-korea-v2.0.1-simple-ux.git.bundle
```

Push from an authenticated environment:

```bash
git push origin main arnis-korea-v2.0.1-simple-ux
```

The tag push starts `.github/workflows/release-arnis-korea.yml`.

## Default screen

The beginner UI shows only:

- `1. 시작하기`
- `2. 지도 만들기`
- `3. 마인크래프트로 내보내기`
- 새 지도 만들기
- 기존 프로젝트 열기
- 최근 프로젝트
- 도움말
- 네이버 API 키 상태
- API 키 설정
- bottom `로그` and `문제 해결`

`API 키 설정`, `도움말`, and `문제 해결` open small beginner dialogs. The full advanced notebook opens only through `고급 설정 열기`.

## Hidden from default UI

These remain available only through advanced settings or troubleshooting paths:

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

- project create/open/save
- Naver API key save/delete/test
- Static Map background
- AI candidates
- approved layers
- layer editing
- world generation
- Minecraft saves copy
- dev-tools CLI/debug/renderer/AI worker packaging

## Local verification already run

```bash
python -m py_compile scripts/arnis_korea_gui.py
PYTHONPATH=src python -m arnis_korea_detailed.trace_editor_core self-test --output-dir /tmp/arnis-simple-ux-trace-troubleshooting-dialog
PYTHONPATH=src python -m arnis_korea_detailed.trace_worldgen self-test --output-dir /tmp/arnis-simple-ux-world-smoke-final-audit
xvfb-run -a python scripts/arnis_korea_gui.py --self-test-gui
xvfb-run -a python scripts/arnis_korea_gui.py --safe-mode --self-test-gui
xvfb-run -a python scripts/arnis_korea_gui.py --self-test-simple-wizard
xvfb-run -a python scripts/arnis_korea_gui.py --self-test-beginner-flow
xvfb-run -a python scripts/arnis_korea_gui.py --self-test-advanced-mode
python scripts/release_scan.py .
git diff --check
```

## Windows Actions evidence to collect

After Actions succeeds, record:

- Actions run URL
- artifact id
- artifact name
- SHA256 from `SHA256SUMS.windows`
- `MANIFEST.windows.txt`

Required Windows gates:

- packaged `arnis-korea.exe --self-test-gui` PASS
- packaged `arnis-korea.exe --safe-mode --self-test-gui` PASS
- packaged `arnis-korea.exe --self-test-simple-wizard` PASS
- packaged `arnis-korea.exe --self-test-beginner-flow` PASS
- packaged `arnis-korea.exe --self-test-advanced-mode` PASS
- packaged `dev-tools\arnis-korea-debug.exe --self-test-gui` PASS
- `latest.log` creation PASS
- mock project to AI candidate to approval to world generation to saves copy simulation PASS
- existing v2.0 QA gates PASS
- source/package secret, raster, world, cache scans PASS
- package root exposes only `arnis-korea.exe`
