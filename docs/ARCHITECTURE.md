# Architecture

Arnis Korea v0.5는 GUI/CLI가 같은 Python core를 호출하고, Naver-only 모드에서는 외부 지도 네트워크를 차단한 자체 Java Anvil writer로 world를 생성합니다.

## 구성

- `scripts/arnis_korea_gui.py`: tkinter Windows GUI, 기본 source는 `naver-only`
- `scripts/arnis_korea_detailed.py`: CLI entrypoint
- `src/arnis_korea_detailed/source_policy.py`: Naver-only source policy와 report
- `src/arnis_korea_detailed/static_map_request_planner.py`: Static Map request plan
- `src/arnis_korea_detailed/naver_static_map_provider.py`: 공식 Static Map probe/download
- `src/arnis_korea_detailed/segment_map_image.py`: raster color segmentation
- `src/arnis_korea_detailed/vectorize_features.py`: connected component vectorization
- `src/arnis_korea_detailed/geometry_cleanup.py`: small object cleanup
- `src/arnis_korea_detailed/naver_synthetic_layer.py`: synthetic feature layer
- `src/arnis_korea_detailed/minimal_world_writer.py`: no-network Java world writer

## 흐름

1. GUI/CLI에서 bbox와 옵션을 입력합니다.
2. `plan-static`이 공식 Static Map 요청 수와 params를 계산합니다.
3. 사용자가 저장/분석 동의와 조건 확인을 명시한 경우에만 raster를 저장합니다.
4. raster를 segment/vectorize/cleanup합니다.
5. `features.normalized.json`을 작성합니다.
6. Naver-derived synthetic layer를 작성합니다.
7. minimal writer가 `level.dat`와 `region/*.mca`를 생성합니다.
8. quality report와 source-policy report를 작성합니다.

## Renderer 선택

v0.5는 patched upstream Arnis renderer 대신 `arnis_korea_minimal_anvil_writer`를 사용합니다. 이 writer는 process 안에서 동작하며 외부 HTTP를 호출하지 않습니다.
