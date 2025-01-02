# Changelog
## [1.5.10a] - 2025-01-02

### 개선됨
- 웹UI 설정 페이지 개선

## [1.5.10] - 2025-01-01

### 개선됨
- webUI상 설정 저장 및 검증 기능 강화

## [1.5.9] - 2025-01-01

### 개선됨
- 웹 서버 기능 및 UI 상호작용 강화
  - 기기 새로고침 기능 구현

## [1.5.8] - 2025-01-01

### 개선됨
- 큐 처리 로직 개선: 큐 재시도가 완료된 후 다음 큐를 실행하도록 개선
- 온도관련 패킷 처리 로직 개선
- 큐 처리 간격 조정 (150ms -> 130ms)이상 여유있을 때 큐를 처리함

### 수정됨
- 온도값 변환 함수 오류 수정

## [1.5.7] - 2024-12-31

### 개선됨
- 웹UI 패킷 처리 로직 최적화

## [1.5.6] - 2024-12-31

### 수정됨
- 온도조절기 예상패킷 생성이 제대로 되지 않던 문제 수정
- 중복 코드 제거 및 참조 업데이트
- 코드 가독성 및 유지보수성 향상

## [1.5.5] - 2024-12-31

### 추가됨
- 설정 및 기능 개선
  - 최소 수신 횟수를 설정하여 예상패킷이 이 횟수만큼 수신되어야 명령 패킷 전송에 성공한것으로 판단합니다.
  - 새로운 설정 옵션 추가
    - min_receive_count: 패킷 전송 성공 판단을 위한 최소 수신 횟수
    - climate_min_temp: 온도조절기 최저 온도 제한 (기본 값 5°C)
    - climate_max_temp: 온도조절기 최고 온도 제한 (기본 값 40°C)
  - 웹 인터페이스 개선
    - 실시간 패킷 로그 일시정지/재개 기능
    - 패킷 로그 다운로드 기능

## [1.5.4] - 2024-12-27

### 변경됨
- 애드온 구조 및 API 상호작용 개선
  - Dockerfile 최적화
    - slim-bookworm 기반 Python 이미지로 변경
  - 설정 저장 로직 개선
    - bashio_wrapper.sh 스크립트 제거
    - 직접 API 요청 방식으로 변경
  - 웹 서버 기능 강화
    - API 호출 실패 시 에러 처리 개선
    - vendor 설정 변경 시 현재 설정 확인 로직 추가

## [1.5.3] - 2024-12-27

### 변경됨
- 애드온 구성 및 설정 저장 로직 개선
  - Dockerfile alpine 기반 Python 이미지로 변경
  - 설정 저장 로직 개선
    - 변경된 설정만 저장하도록 수정
    - 설정 저장 후 애드온 자동 재시작
    