# Architecture

Arnis Korea는 Windows GUI와 CLI가 같은 Python core를 공유하고, 실제 Minecraft Java world 생성은 upstream Arnis binary에 위임합니다.

## 구성

- `scripts/arnis_korea_gui.py`: tkinter 기반 Windows GUI
- `scripts/arnis_korea_detailed.py`: CLI entrypoint
- `src/arnis_korea_detailed/arnis_wrapper.py`: upstream Arnis command mapping
- `src/arnis_korea_detailed/static_map_request_planner.py`: Static Map 요청 계획
- `src/arnis_korea_detailed/naver_static_map_provider.py`: 공식 Static Map 단건 probe/download
- `web/dynamic_selector.html`: bbox 선택용 local HTML

## 실행 흐름

1. GUI가 bbox와 생성 옵션을 수집합니다.
2. GUI가 `arnis-korea-cli.exe generate` 명령을 생성해 실행합니다.
3. CLI가 입력을 검증하고 metadata를 기록합니다.
4. `arnis_wrapper`가 `bin/arnis-upstream.exe`에 bbox, terrain, interior, roof, spawn 옵션을 전달합니다.
5. 생성 결과에서 `level.dat`, `region`, `.mca` 파일 존재를 확인합니다.

## Naver API

Naver Static Map은 공식 endpoint만 사용합니다. GUI 테스트는 단건 요청으로 status, content-type, bytes, sha256 prefix만 표시하고 이미지를 저장하지 않습니다.
