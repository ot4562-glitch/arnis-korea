# Paper 26.1.2 Compatibility Gate

v1.1 release gate는 world folder 생성만으로 PASS하지 않습니다.

## 필수 조건

- `level.dat` 존재
- `session.lock` 존재
- `region/*.mca` 존재
- world root에 reports, naver_raster, previews, layer JSON 없음
- 임시 Paper 서버에서 world load smoke PASS

## Load Smoke

Actions는 별도 임시 서버 디렉터리를 만들고 다음 설정으로 실행합니다.

- `eula=true`
- `online-mode=false`
- `enable-rcon=false`
- `nogui`
- live server 사용 금지
- timeout 120~240초

로그에서 정상 load 신호를 확인하고 crash report, fatal chunk/level 오류가 있으면 실패합니다.

Paper 26.1.2 호환 jar를 확보하지 못하면 fallback smoke를 성공으로 처리하지 않습니다.
