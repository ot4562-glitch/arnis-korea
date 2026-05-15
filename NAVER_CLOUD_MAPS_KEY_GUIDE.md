# Naver Cloud Maps Key Guide

Arnis Korea v0.9는 공식 Naver Static Map API를 배경 지도용으로 사용합니다. 네이버 공식 API 무료 사용량 범위 안에서 개인 개발용으로 테스트하는 것을 전제로 합니다.

## 필요한 값

- Client ID
- Client Secret

Ncloud 계정의 Access Key/Secret Key가 아니라 Maps Application 인증 정보입니다.

## GUI 저장

`네이버 API` 탭에서 값을 입력하고 `저장`을 누릅니다.

저장 위치:

```text
%APPDATA%\ArnisKorea\secrets.json
```

GUI 로그, 프로젝트 파일, artifact에는 키 원문을 쓰지 않습니다. API 테스트 결과는 HTTP status, content-type, bytes, sha256 prefix만 표시합니다.

## 사용 정책

- 공식 Static Map API만 raster 배경 입력으로 사용합니다.
- 저장/분석 동의가 있을 때만 raster를 프로젝트의 `naver_raster/` 아래에 저장합니다.
- Dynamic Map은 bbox 선택 보조 UI로만 사용합니다.
- 비공식 scraping 또는 내부 지도 데이터 접근은 사용하지 않습니다.
