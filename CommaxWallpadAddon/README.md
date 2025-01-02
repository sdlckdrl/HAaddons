# Commax Wallpad Addon for Home Assistant

코맥스 월패드를 Home Assistant에 연동하기 위한 애드온입니다.
EW-11 전용입니다. usb-serial 통신은 지원하지 않습니다.

이 애드온은 [@kimtc99](https://github.com/kimtc99/HAaddons)의 'CommaxWallpadBySaram' 애드온을 기반으로 작성되었으며 mqtt를 통해 ew11과 통신을 하는 특징이 있습니다.

- 명령 패킷 전송 시 예상되는 상태 패킷을 미리 계산하여 저장합니다.
- 예상된 상태 패킷이 수신될 때까지 명령 패킷을 자동으로 재전송합니다.
- 이를 통해 통신의 신뢰성을 높이고 명령이 제대로 처리되었는지 확인할 수 있습니다.
- 설정된 최대 재시도 횟수에 도달하면 재전송을 중단합니다.

다만 애드온을 거의 새로 작성하면서 저희집 월패드가 보일러만 있기 떄문에 보일러만 테스트 되었고 나머지 기능은 구현만 되어있습니다.

## 지원하는 기능
- 조명 제어 (테스트 안되어있음)
- 난방 제어
- 콘센트 제어 (테스트 안되어있음, 전력량 미지원)
- 전열교환기 제어 (테스트 안되어있음)
- 가스밸브 상태 확인 (테스트 안되어있음)
- 엘리베이터 호출 (테스트 안되어있음)

## 설치 방법
1. Home Assistant의 Supervisor > Add-on Store에서 저장소 추가
2. 다음 URL을 저장소에 추가: `https://github.com/sdlckdrl/HAaddons`
3. 애드온 스토어에서 "Commax Wallpad Addon" 검색
4. "Install" 클릭 후 설치 진행

## EW11 mqtt 설정 방법 (필수!!)
EW11 관리페이지의 Community Settings에서 mqtt를 추가하고 다음과 같이 설정하세요:

### Basic Settings
- Name: mqtt
- Protocol: MQTT

### Socket Settings
- Server: 192.168.0.39 (MQTT 브로커의 IP 주소)
- Server Port: 1883
- Local Port: 0
- Buffer Size: 512
- Keep Alive(s): 60
- Timeout(s): 300

### Protocol Settings
- MQTT Version: 3
- MQTT Client ID: ew11-mqtt
- MQTT Account: my_user (mosquitto broker 애드온의 구성에서 확인하세요.)
- MQTT Password: m1o@s#quitto (mosquitto broker 애드온의 구성에서 확인하세요.)
- Subscribe Topic: ew11/send
- Subscribe QoS: 0
- Publish Topic: ew11/recv
- Publish QoS: 0
- Ping Period(s): 1

### More Settings
- Security: Disable
- Route: Uart

## 애드온 설정 방법
애드온 구성에서 다음 옵션들을 설정하세요:

### MQTT 설정
- `mqtt_server`: MQTT 브로커의 IP 주소 (예: "192.168.0.39")
- `mqtt_id`: MQTT 브로커 로그인 아이디 (mosquitto broker 애드온의 구성에서 확인하세요.)
- `mqtt_password`: MQTT 브로커 로그인 비밀번호 (mosquitto broker 애드온의 구성에서 확인하세요.)
- `mqtt_TOPIC`: MQTT 토픽 이름 (기본값: "commax", 수정 필요 없음)

### EW11 (Elfin) 설정 
- `elfin_auto_reboot`: EW11 자동 재부팅 사용 여부 (true/false)
- `elfin_server`: EW11 장치의 IP 주소 (ew11 재시작 기능을 위해 필요합니다. 아닌경우 기본값으로 두셔도됩니다.)
- `elfin_id`: EW11 관리자 아이디 (기본값: "admin") (ew11 재시작 기능을 위해 필요합니다. 아닌경우 기본값으로 두셔도됩니다.)
- `elfin_password`: EW11 관리자 비밀번호 (ew11 재시작 기능을 위해 필요합니다. 아닌경우 기본값으로 두셔도됩니다.)
- `elfin_reboot_interval`: EW11 자동 재부팅 간격, 설정된 시간만큼 ew11로부터 신호를 받지 못하면 재부팅을 시도합니다. (초 단위, 기본값: 60)

### 기타 설정
- `queue_interval_in_second`: 명령패킷 전송 간격 (초 단위, 기본값: 0.1 (100ms)), 너무 작은 값을 설정하면 명령패킷 전송이 너무 빠르게 이루어져 명령이 제대로 처리되지 않을 수 있습니다. 이 설정값과 관계없이 상태패킷 수신이 130ms 이상 유휴중일때만 명령패킷을 전송합니다.
- `max_send_count`: 명령패킷 최대 재시도 횟수 (기본값: 15, 범위 1-99) 값을 높일 수록 연속된 명령을 보낼 때 딜레이가 커질 수 있습니다.
- `min_receive_count`: 패킷 전송 성공으로 판단할 예상패킷 최소 수신 횟수 (기본값: 1, 범위 1-9) 값을 높일 수록 연속된 명령을 보낼 때 딜레이가 커질 수 있습니다.
- `DEBUG`: 디버그 로그 출력 여부 (true/false)
- `mqtt_log`: MQTT 로그 출력 여부 (true/false)
- `elfin_log`: EW11 로그 출력 여부 (true/false)
- `vendor`: 기기 패킷 구조 파일 선택 (commax/custom 선택), custom을 선택한경우 /share/packet_structures_custom.yaml을 우선적으로 적용하게됩니다. 패킷정보가 다른경우 수정해서 쓸 수 있습니다. 기기구조 파일은 웹UI에서도 수정할 수 있습니다.
- `climate_min_temp`: 온도조절기 최저 온도 제한 (기본값: 5°C)
- `climate_max_temp`: 온도조절기 최고 온도 제한 (기본값: 40°C)

설정 예시:
```yaml
queue_interval_in_second: 0.1
max_send_count: 15
min_receive_count: 1
climate_min_temp: 5
climate_max_temp: 40
DEBUG: false
mqtt_log: false
elfin_log: false
mqtt_server: "192.168.0.13" # HA 서버의 IP 주소
mqtt_id: "my_user"
mqtt_password: "m1o@s#quitto"
mqtt_TOPIC: "commax"
elfin_auto_reboot: true
elfin_server: "192.168.0.54" # ew11 장치의 IP 주소
elfin_id: "admin"
elfin_password: "admin"
elfin_reboot_interval: 60
vendor: "commax"
```

