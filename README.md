# Arnis Korea v2.0.1 Simple UX

Arnis Korea는 한국 지역을 Minecraft Java 월드로 만들기 위한 개인 개발용 Windows GUI입니다. 공개 배포용이 아니며, GitHub Actions artifact는 개인 Windows PC로 옮기기 위한 산출물입니다.

일반 사용자는 root의 `arnis-korea.exe`만 실행합니다. 첫 화면은 개발자 탭 모음이 아니라 3단계 마법사입니다.

## 기본 화면

1. 시작하기
2. 지도 만들기
3. 마인크래프트로 내보내기

시작하기 화면에는 새 지도 만들기, 기존 프로젝트 열기, 최근 프로젝트, 도움말, 네이버 API 키 상태만 보입니다. 로그와 문제 해결은 하단 작은 버튼으로 접근합니다.

## 유지되는 기능

- 프로젝트 생성, 열기, 저장
- 네이버 공식 Static Map API 키 저장, 삭제, 테스트
- 지도 범위와 스폰포인트 설정
- 네이버 Static Map 또는 샘플 배경 위 수동 편집
- 도로, 철도, 건물, 수역, 녹지, 스폰포인트 생성/선택/수정/삭제
- 확대/축소, 배경 이동, 점 추가/이동/삭제, 실행 취소/다시 실행
- AI 후보 보기, 승인, 승인된 레이어 되돌리기
- 승인된 레이어만 월드 생성 입력으로 사용
- 월드 생성용 변환 데이터 생성
- patched Arnis no-network writer로 `playable_world/<world_name>` 생성
- Paper 26.1.2 마인크래프트 호환성 검사 release gate
- Minecraft saves에는 playable world 폴더만 복사

## 고급 설정

기본 초보자 모드에서는 위험하거나 개발자용인 항목을 숨깁니다. `고급 설정 열기`에서만 레이어 직접 가져오기/내보내기, 검사 결과, 데이터 사용 안전 검사, AI 분석 패키지, debug preview, Paper 호환성 검사, 내부 CLI/renderer 관련 도구에 접근합니다.

## Artifact

```text
arnis-korea-2.0.1-simple-ux-windows_x86_64
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

`dev-tools/`에는 debug, CLI, 월드 생성 엔진, AI 분석 worker 실행 파일이 있을 수 있습니다. root에는 `arnis-korea-cli.exe`를 두지 않습니다.
