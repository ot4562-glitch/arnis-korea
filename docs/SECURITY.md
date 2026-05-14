# Security

## Secret handling

- GitHub token은 저장소, 로그, 릴리스 zip에 포함하지 않습니다.
- Naver Client ID/Client Secret은 exe나 source에 포함하지 않습니다.
- GUI 저장값은 `%APPDATA%\ArnisKorea\secrets.json`에만 저장됩니다.
- GUI와 CLI 로그에는 키 원문을 출력하지 않습니다.

## Release policy

- 릴리스 zip에는 Naver 응답 이미지, cache, 파생 raster 데이터를 포함하지 않습니다.
- 공식 Naver Static Map endpoint 외의 데이터 취득 방식을 사용하지 않습니다.
- live Minecraft server world 경로, RCON, nginx, systemd는 릴리스 작업 대상이 아닙니다.

## Validation

릴리스 전에는 source와 zip에 대해 token 패턴, Naver secret 패턴, 금지된 지도 취득 방식 표현을 검사합니다. 공식 헤더명 설명은 허용됩니다.
