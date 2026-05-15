# v2.0.1 Simple UX Completion Audit

## Objective

Convert Arnis Korea from a visible developer tab collection into a Korean 3-step beginner wizard, keep advanced/dev functions available behind explicit advanced or troubleshooting access, preserve v2.0.0 functionality and QA gates, update release metadata and Korean UX docs, and produce the Windows Actions artifact.

## Prompt-to-artifact checklist

| Requirement | Evidence | Status |
| --- | --- | --- |
| Default UX is 3 steps: 시작하기, 지도 만들기, 마인크래프트로 내보내기 | `scripts/arnis_korea_gui.py` builds the beginner wizard; `--self-test-simple-wizard` checks required labels | Local PASS |
| Default screen shows only new/open/recent/help/API status/API setup plus bottom log/troubleshooting | `--self-test-simple-wizard` checks required beginner labels and forbidden labels | Local PASS |
| source policy, synthetic OSM, debug, reports, schema, artifact, renderer, CLI, AI worker internals, Paper smoke, dev-tools, threshold hidden from default UI | `--self-test-simple-wizard` forbidden-term scan | Local PASS |
| API key setup available from beginner mode without opening advanced mode | `open_api_settings()` opens a small `Toplevel`; self-test checks advanced host remains hidden | Local PASS |
| Help available from beginner mode without opening advanced mode | `show_beginner_help()` popup; self-test checks advanced host remains hidden | Local PASS |
| Troubleshooting available without opening full advanced mode | `open_troubleshooting()` opens a small `Toplevel`; self-test checks advanced host remains hidden | Local PASS |
| Advanced mode opens through one explicit button | `고급 설정 열기`; `--self-test-advanced-mode` | Local PASS |
| Layer terminology Koreanized for user UI | GUI labels use 승인된 레이어, AI 후보, 월드 생성용 변환 데이터, 데이터 사용 안전 검사, 월드 생성 엔진, 지도 범위 | Local PASS |
| Final generation wizard shows five ordered checks and status values | `wizard_status_vars` with `완료`, `필요함`, `오류` | Local PASS |
| Required Korean errors | missing API key, missing approved layer, worldgen failure messages in `scripts/arnis_korea_gui.py` | Local PASS |
| Preserve project/API/static map/AI/layer editing/worldgen/saves/dev-tools functions | `trace_editor_core self-test`, `trace_worldgen self-test`, local final QA simulation | Local PASS |
| GUI boot gates | `--self-test-gui`, `--safe-mode --self-test-gui`; workflow also checks packaged debug exe | Local PASS, Windows pending |
| Latest log creation | workflow `Packaged GUI boot smoke` checks `%APPDATA%\ArnisKorea\logs\latest.log` | Windows pending |
| Actions simple wizard/beginner/advanced checks | `.github/workflows/release-arnis-korea.yml` runs new GUI self-tests before and after packaging | Windows pending |
| Mock project to AI candidate to approval to world generation to saves copy simulation | existing `trace_worldgen final-qa --renderer --load-smoke` workflow gate | Windows pending |
| Existing v2.0 QA gates preserved | workflow still runs trace editor QA and full user-flow QA | Windows pending |
| Artifact secret/raster/world/cache scan | workflow `Source and artifact policy scans` | Windows pending |
| Root exposes only `arnis-korea.exe` | workflow checks root `.exe` list equals only `arnis-korea.exe` | Windows pending |
| Version and artifact metadata | `__version__`, `trace_editor_core VERSION`, workflow artifact name, docs | Local PASS |
| Korean UX docs updated | `README.md`, `WINDOWS_QUICKSTART.md`, `docs/TRACE_EDITOR_USER_GUIDE.md`, `docs/RELEASE_V2_0_1_SIMPLE_UX.md` | Local PASS |
| Commit/tag report | local commit and tag exist | Local PASS |
| Actions run URL, artifact id/name/SHA256 | requires authenticated push and successful Actions run | Blocked |

## Current blocker

The local workspace has no GitHub authentication. `git push origin main arnis-korea-v2.0.1-simple-ux` fails with:

```text
fatal: could not read Username for 'https://github.com': No such device or address
```

Until the tag is pushed and the Windows workflow succeeds, the objective is not fully complete.
