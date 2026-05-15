# Private Dev Notes

이 프로젝트는 개인 개발용입니다. 공개 GitHub Release를 만들지 않고 Actions artifact만 사용합니다.

금지된 작업:
- secret 원문 출력
- 비공식 Naver scraping
- live Minecraft/RCON/nginx/systemd touch
- OSM/Overpass/Overture/AWS/ESA/Nominatim 호출

최종 gate는 mock QA, GUI boot QA, final user-flow QA, Paper 26.1.2 load smoke, source/artifact scan입니다.

## AI Trace Worker

AI Trace는 Windows EXE 내부 모델이 아니라 OCI 내부 worker 또는 dev-tools CLI로 실행합니다. GUI는 분석 패키지를 내보내고 결과를 suggested 후보로 가져옵니다. 사용자가 승인한 accepted layer만 월드 생성에 사용됩니다.
