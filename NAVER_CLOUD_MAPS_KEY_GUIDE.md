# Naver Cloud Maps 키 설정 가이드

Arnis Korea GUI는 Naver Cloud Maps Application의 Client ID와 Client Secret을 사용합니다. Ncloud 계정의 Access Key/Secret Key가 아닙니다.

## 키 찾기

1. Naver Cloud Platform Console에 접속합니다.
2. `Services` 또는 `Product & Services` 메뉴로 이동합니다.
3. `Application Services`를 엽니다.
4. `Maps`를 선택합니다.
5. `Application 관리`로 이동합니다.
6. 새 Application을 생성하거나 기존 Application을 선택합니다.
7. 사용할 API 목록에서 `Static Map`을 체크합니다.
8. bbox selector를 사용할 경우 `Dynamic Map`도 체크합니다.
9. 설정을 저장합니다.
10. Application 인증 정보를 확인합니다.
11. `Client ID`를 복사합니다.
12. `Client Secret`을 복사합니다.
13. Arnis Korea 앱의 `네이버 API` 탭에 붙여넣습니다.
14. `Save Key` 또는 `저장`을 누릅니다.
15. `Test Static Map API` 또는 `Static Map API 테스트`를 누릅니다.
16. 결과가 `200`이고 `content-type`이 `image/png`이면 성공입니다.

## 401 응답이 나올 때

- Client ID와 Client Secret이 서로 맞지 않을 수 있습니다.
- Maps Application에서 Static Map을 체크하지 않았을 수 있습니다.
- Ncloud 계정 Access Key/Secret Key를 잘못 넣었을 수 있습니다.

다시 강조하면, 앱에 넣는 값은 Ncloud Access Key/Secret Key가 아니라 Maps Application의 Client ID/Client Secret입니다.

## 공식 endpoint

```text
https://maps.apigw.ntruss.com/map-static/v2/raster
```

인증 헤더 이름:

```text
x-ncp-apigw-api-key-id
x-ncp-apigw-api-key
```

앱과 배포물에는 키가 포함되지 않습니다. GUI에서 저장한 키는 사용자 PC의 `%APPDATA%\ArnisKorea\secrets.json`에만 저장됩니다.
