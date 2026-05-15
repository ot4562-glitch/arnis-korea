# Paper 26.1.2 Compatibility Gate

v2.0.0 private-final은 파일 존재만으로 PASS하지 않습니다. release gate는 Paper 26.1.2 서버에서 load smoke를 통과해야 합니다.

## 검사

- `level.dat` 존재
- `session.lock` 존재
- `region/*.mca` 존재
- world root에 reports, naver_raster, previews, JSON/MD metadata 없음
- Paper 26.1.2 로그에 정상 load 신호 존재
- crash report와 fatal chunk/level 오류 없음

## 실행 조건

- 별도 임시 서버 디렉터리 사용
- `eula=true`
- `online-mode=false`
- `enable-rcon=false`
- `nogui`
- live server 사용 금지

Paper 26.1.2 jar 확보가 실패하면 fallback smoke를 성공으로 처리하지 않습니다.
