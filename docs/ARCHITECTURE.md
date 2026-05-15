# Architecture

Arnis Korea v0.7.0은 GUI/CLI가 같은 Python core를 호출하고, Naver-only 모드에서는 synthetic OSM-like local file을 patched upstream Arnis no-network renderer에 전달해 Java world를 생성합니다. 릴리스 PASS 기준은 Minecraft headless load smoke입니다.

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
- `src/arnis_korea_detailed/arnis_no_network_renderer.py`: patched Arnis renderer wrapper
- `src/arnis_korea_detailed/minimal_world_writer.py`: `custom-debug` only writer, release path 아님
- `src/arnis_korea_detailed/minecraft_load_smoke.py`: 임시 Minecraft Java server load smoke

## 흐름

1. GUI/CLI에서 bbox와 옵션을 입력합니다.
2. `plan-static`이 공식 Static Map 요청 수와 params를 계산합니다.
3. 사용자가 저장/분석 동의와 조건 확인을 명시한 경우에만 raster를 저장합니다.
4. raster를 segment/vectorize/cleanup합니다.
5. `features.normalized.json`을 작성합니다.
6. Naver-derived synthetic OSM-like layer를 작성합니다.
7. patched Arnis renderer가 `--file naver_synthetic_osm.json`로 Java world를 생성합니다.
8. 생성된 Arnis world folder를 사용자가 지정한 `world_name`으로 정리합니다.
9. quality report, source-policy report, world validation report를 metadata 폴더에 작성합니다.
10. Actions에서 `minecraft_load_smoke.json`을 생성하고 PASS를 확인합니다.

## Renderer 선택

v0.7.0 release path는 `patched_arnis_no_network_renderer`입니다. `arnis_korea_minimal_anvil_writer`는 compatibility warning이 붙는 `custom-debug` path입니다.
