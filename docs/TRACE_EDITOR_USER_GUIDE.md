# Trace Editor User Guide

Arnis Korea v2.0.0 private-final은 네이버 지도 배경 위에 사용자가 직접 레이어를 만들고, 승인된 accepted layer만으로 Minecraft Java 월드를 생성하는 GUI입니다.

## 핵심 원칙

- suggested layer는 후보입니다.
- accepted layer만 export와 worldgen 입력입니다.
- Minecraft saves에는 `playable_world/<world_name>`만 복사합니다.

## 레이어 타입

- road: polyline
- rail: polyline
- building: polygon
- water: polygon
- green: polygon
- spawn: point

## 편집

- 그리기: 지도 위를 클릭해 점을 추가하고 `feature 저장`을 누릅니다.
- 선택: feature/점을 클릭하고 드래그해 이동합니다.
- 이동: 배경을 pan 합니다.
- 휠 또는 `+`, `-`, `Reset`으로 zoom을 조정합니다.
- `선택 점 삭제`, `선택 feature 삭제`, `Undo`, `Redo`를 사용할 수 있습니다.
- 이름, 메모, class 변경은 선택 feature에 적용됩니다.

## 최종 생성 마법사

1. 프로젝트 상태 체크
2. synthetic OSM 미리보기 생성
3. 월드 생성 실행
4. 선택적으로 로컬 Paper 26.1.2 smoke 실행
5. playable world 열기 또는 Minecraft saves로 복사

## 문제 해결

`문제 해결` 탭에서 latest.log, reports, project validation, source policy validation을 확인할 수 있습니다.

## AI Trace Worker

AI Trace는 Windows EXE 내부 모델이 아니라 OCI 내부 worker 또는 dev-tools CLI로 실행합니다. GUI는 분석 패키지를 내보내고 결과를 suggested 후보로 가져옵니다. 사용자가 승인한 accepted layer만 월드 생성에 사용됩니다.
