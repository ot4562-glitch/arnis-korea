# AI Trace Worker

AI Trace는 Windows EXE 내부에 무거운 모델을 넣지 않습니다. Windows GUI는 패키지 내보내기와 결과 가져오기만 담당합니다.

## 흐름

1. Windows GUI에서 프로젝트와 Static Map raster를 준비합니다.
2. `AI Trace` 탭에서 OCI AI 분석용 패키지를 내보냅니다.
3. OCI에서 `scripts/ai_trace_worker.py` 또는 `dev-tools/arnis-korea-ai-trace-worker.exe`를 실행합니다.
4. worker는 deterministic CV로 suggested 후보를 생성합니다.
5. Windows GUI에서 AI 결과를 가져옵니다.
6. 결과는 suggested 후보로 병합됩니다. 사용자가 승인해야 accepted layer가 됩니다.

## 출력

```text
suggested_layers.geojson
auto_accepted_layers.geojson
rejected_low_confidence.geojson
ai_trace_report.json
ai_trace_preview.png
confidence_heatmap.png
```

`auto_accepted_layers.geojson`은 confidence gate 통과 후보라는 뜻입니다. Windows GUI는 이를 accepted layer에 바로 넣지 않습니다.

## 금지

- Windows artifact에 AI model/key 포함 금지
- OSM/Overpass/Overture/AWS/ESA/Nominatim 호출 금지
- 비공식 Naver scraping 금지
- confidence 없는 AI 결과를 accepted로 넣기 금지
