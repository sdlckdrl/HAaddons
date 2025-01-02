from flask import Flask, render_template, jsonify, request # type: ignore
import threading
import logging
import os
from typing import Dict, Any
import time
import json
import yaml # type: ignore
import shutil
from datetime import datetime
import requests # type: ignore
from utils import checksum
from gevent.pywsgi import WSGIServer # type: ignore
from geventwebsocket.handler import WebSocketHandler # type: ignore
import gevent # type: ignore

class WebServer:
    def __init__(self, wallpad_controller):
        self.app = Flask(__name__, template_folder='templates')
        self.wallpad_controller = wallpad_controller
        self.recent_messages = []  # 최근 메시지를 저장할 리스트
        self.server = None  # WSGIServer 인스턴스를 저장할 변수
        self.logger = wallpad_controller.logger  # wallpad_controller의 logger 사용
        self.logger.info("웹서버 초기화 완료")
        # 로깅 비활성화
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        # Home Assistant Ingress 베이스 URL 설정
        self.base_url = os.environ.get('SUPERVISOR_TOKEN', '')
        
        # 라우트 설정
        @self.app.route('/')
        def home():
            return render_template('index.html')

        @self.app.route('/ws')
        def websocket():
            self.logger.info("웹소켓 요청 수신")
            wsgi_websocket = request.environ.get('wsgi.websocket')
            
            if not wsgi_websocket:
                self.logger.error("웹소켓 연결 실패 - wsgi.websocket이 없음")
                return 'WebSocket connection failed'

            self.logger.info(f"웹소켓 환경 정보: {request.environ.get('HTTP_UPGRADE', '정보없음')}")
            self.logger.info(f"웹소켓 프로토콜: {request.environ.get('HTTP_SEC_WEBSOCKET_PROTOCOL', '정보없음')}")
            
            ws = request.environ['wsgi.websocket']
            self.logger.info("새로운 웹소켓 연결 수립됨")

            try:
                last_send_data = set()
                last_recv_data = set()
                last_ping_time = time.time()
                
                # 초기 연결 확인 메시지 전송
                try:
                    ws.send(json.dumps({
                        'type': 'connection_established',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                        'send_data': list(self.wallpad_controller.COLLECTDATA['send_data']),
                        'recv_data': list(self.wallpad_controller.COLLECTDATA['recv_data'])
                    }))
                    self.logger.info("초기 연결 확인 메시지 전송됨")
                except Exception as e:
                    self.logger.error(f"초기 메시지 전송 실패: {e}")
                    return ''
                
                while not ws.closed:
                    try:
                        # 30초마다 ping 전송
                        current_time = time.time()
                        if current_time - last_ping_time > 30:
                            try:
                                ws.send(json.dumps({
                                    'type': 'ping',
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                                }))
                                last_ping_time = current_time
                                self.logger.debug("Ping 전송됨")
                            except Exception as ping_error:
                                self.logger.error(f"Ping 전송 오류: {ping_error}")
                                break
                        
                        current_send_data = set(self.wallpad_controller.COLLECTDATA['send_data'])
                        current_recv_data = set(self.wallpad_controller.COLLECTDATA['recv_data'])
                        
                        # 변경된 데이터가 있는 경우에만 전송
                        if current_send_data != last_send_data or current_recv_data != last_recv_data:
                            data = {
                                'type': 'packet_data',
                                'send_data': list(current_send_data),
                                'recv_data': list(current_recv_data),
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                            }
                            try:
                                ws.send(json.dumps(data))
                                last_send_data = current_send_data
                                last_recv_data = current_recv_data
                                self.logger.debug("패킷 데이터 전송됨")
                            except Exception as send_error:
                                self.logger.error(f"데이터 전송 오류: {send_error}")
                                break
                        
                        # 메시지 수신 대기 (non-blocking)
                        try:
                            msg = ws.receive()
                            if msg is None:  # 연결이 종료됨
                                self.logger.info("클라이언트가 연결을 종료함")
                                break
                            elif msg:  # 메시지가 있는 경우
                                try:
                                    data = json.loads(msg)
                                    if data.get('type') == 'pong':
                                        self.logger.debug("Pong 수신됨")
                                    else:
                                        self.logger.debug(f"클라이언트로부터 메시지 수신: {msg}")
                                except json.JSONDecodeError:
                                    self.logger.error(f"잘못된 JSON 형식: {msg}")
                        except Exception as recv_error:
                            if not ws.closed:
                                self.logger.error(f"메시지 수신 오류: {recv_error}")
                                break

                        gevent.sleep(0.1)  # 100ms 마다 업데이트
                        
                    except Exception as loop_error:
                        self.logger.error(f"웹소켓 루프 오류: {loop_error}")
                        break
                        
            except Exception as e:
                self.logger.error(f"웹소켓 처리 중 오류 발생: {e}")
            finally:
                if not ws.closed:
                    try:
                        ws.close()
                    except Exception as close_error:
                        self.logger.error(f"웹소켓 종료 중 오류: {close_error}")
                self.logger.info("웹소켓 연결 종료됨")
            return ''

        @self.app.route('/api/custom_packet_structure/editable', methods=['GET'])
        def get_editable_packet_structure():
            """편집 가능한 패킷 구조 필드를 반환합니다."""
            try:
                custom_file = '/share/packet_structures_custom.yaml'
                if os.path.exists(custom_file):
                    with open(custom_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                else:
                    with open('/apps/packet_structures_commax.yaml', 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)

                editable_structure = {}
                for device_name, device_data in data.items():
                    editable_structure[device_name] = {
                        'type': device_data.get('type', ''),
                        'command': self._get_editable_fields(device_data.get('command', {})),
                        'state': self._get_editable_fields(device_data.get('state', {})),
                        'state_request': self._get_editable_fields(device_data.get('state_request', {})),
                        'ack': self._get_editable_fields(device_data.get('ack', {}))
                    }
                return jsonify({'content': editable_structure, 'success': True})
            except Exception as e:
                return jsonify({'error': str(e), 'success': False})

        @self.app.route('/api/custom_packet_structure/editable', methods=['POST'])
        def save_editable_packet_structure():
            """편집된 패킷 구조를 기존 구조와 병합하여 저장합니다."""
            try:
                content = request.json.get('content', {})
                
                # 현재 패킷 구조 로드
                custom_file = '/share/packet_structures_custom.yaml'
                if os.path.exists(custom_file):
                    with open(custom_file, 'r', encoding='utf-8') as f:
                        current_data = yaml.safe_load(f)
                else:
                    with open('/apps/packet_structures_commax.yaml', 'r', encoding='utf-8') as f:
                        current_data = yaml.safe_load(f)

                # 편집된 내용을 현재 구조와 병합
                for device_name, device_data in content.items():
                    if device_name not in current_data:
                        current_data[device_name] = {}
                    
                    current_data[device_name]['type'] = device_data.get('type', current_data[device_name].get('type', ''))
                    
                    for packet_type in ['command', 'state', 'state_request', 'ack']:
                        if packet_type in device_data:
                            self._merge_packet_structure(
                                current_data[device_name].setdefault(packet_type, {}),
                                device_data[packet_type]
                            )

                # 백업 생성
                backup_dir = '/share/packet_structure_backups'
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                
                if os.path.exists(custom_file):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_file = f'{backup_dir}/packet_structures_custom_{timestamp}.yaml'
                    shutil.copy2(custom_file, backup_file)

                # 새 내용 저장
                with open(custom_file, 'w', encoding='utf-8') as f:
                    yaml.dump(current_data, f, allow_unicode=True, sort_keys=False)

                # 컨트롤러의 패킷 구조 다시 로드
                self.wallpad_controller.load_devices_and_packets_structures()

                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e), 'success': False})

        @self.app.route('/api/devices')
        def get_devices():
            return jsonify(self.wallpad_controller.device_list or {})
            
        @self.app.route('/api/state')
        def get_state():
            return jsonify(self.wallpad_controller.HOMESTATE)

        @self.app.route('/api/mqtt_status')
        def get_mqtt_status():
            """MQTT 연결 상태 정보를 제공합니다."""
            if not self.wallpad_controller.mqtt_client:
                return jsonify({
                    'connected': False,
                    'broker': None,
                    'client_id': None,
                    'subscribed_topics': []
                })

            client = self.wallpad_controller.mqtt_client
            return jsonify({
                'connected': client.is_connected(),
                'broker': f"{self.wallpad_controller.config['mqtt_server']}",
                'client_id': client._client_id.decode() if client._client_id else None,
                'subscribed_topics': [
                    f'{self.wallpad_controller.HA_TOPIC}/+/+/command',
                    f'{self.wallpad_controller.ELFIN_TOPIC}/recv',
                    f'{self.wallpad_controller.ELFIN_TOPIC}/send'
                ]
            })

        @self.app.route('/api/config', methods=['GET'])
        def get_config():
            """CONFIG 객체의 내용과 스키마를 제공합니다."""
            # 하드코딩된 schema 정보 from config.json
            schema = {
                "DEBUG": "bool",
                "mqtt_log": "bool",
                "elfin_log": "bool",
                "vendor": "list(commax|custom)",
                "queue_interval_in_second": "float(0.01,1.0)",
                "max_send_count": "int(1,99)",
                "min_receive_count": "int(1,9)",
                "climate_min_temp": "int(0,19)",
                "climate_max_temp": "int(20,99)",
                "mqtt_server": "match(^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$)",
                "mqtt_id": "str",
                "mqtt_password": "str",
                "mqtt_TOPIC": "str",
                "elfin_auto_reboot": "bool",
                "elfin_server": "match(^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}$)?",
                "elfin_id": "str?",
                "elfin_password": "str?",
                "elfin_reboot_interval": "int"
            }
            return jsonify({
                'config': self.wallpad_controller.config,
                'schema': schema
            })
        
        @self.app.route('/api/config', methods=['POST'])
        def save_config():
            """설정을 저장하고 컨트롤러에 적용합니다."""
            try:
                data = request.json
                if not data:
                    return jsonify({'error': '설정 데이터가 없습니다.'}), 400

                # 현재 설정 파일 읽기
                with open('/data/options.json', 'r', encoding='utf-8') as f:
                    current_options = json.load(f)

                schema = current_options.get('schema', {})
                
                # 스키마 기반 유효성 검사
                validation_errors = []
                for key, value in data.items():
                    if key in schema:
                        field_schema = schema[key]
                        schema_type = field_schema.split('(')[0]  # list(commax|custom) -> list
                        
                        # 필수/선택 필드 확인
                        is_optional = field_schema.endswith('?')
                        if not is_optional and value is None:
                            validation_errors.append(f"{key}: 필수 항목입니다.")
                            continue
                            
                        if value is not None:  # 값이 있는 경우에만 타입 검사
                            # 타입 검사
                            if schema_type == 'int':
                                try:
                                    val = int(value)
                                    # int(min,max) 형식에서 범위 추출
                                    if '(' in field_schema:
                                        range_str = field_schema.split('(')[1].rstrip('?)')
                                        if ',' in range_str:
                                            min_val, max_val = map(int, range_str.split(','))
                                            if val < min_val or val > max_val:
                                                validation_errors.append(f"{key}: {min_val}에서 {max_val} 사이의 값이어야 합니다.")
                                except (ValueError, TypeError):
                                    validation_errors.append(f"{key}: 정수여야 합니다.")
                            elif schema_type == 'float':
                                try:
                                    val = float(value)
                                    # float(min,max) 형식에서 범위 추출
                                    if '(' in field_schema:
                                        range_str = field_schema.split('(')[1].rstrip('?)')
                                        if ',' in range_str:
                                            min_val, max_val = map(float, range_str.split(','))
                                            if val < min_val or val > max_val:
                                                validation_errors.append(f"{key}: {min_val}에서 {max_val} 사이의 값이어야 합니다.")
                                except (ValueError, TypeError):
                                    validation_errors.append(f"{key}: 실수여야 합니다.")
                            elif schema_type == 'bool':
                                if not isinstance(value, bool):
                                    validation_errors.append(f"{key}: 참/거짓 값이어야 합니다.")
                            elif schema_type == 'list':
                                # list(commax|custom) 형식에서 가능한 값들 추출
                                allowed_values = field_schema.split('(')[1].rstrip('?)').split('|')
                                if value not in allowed_values:
                                    validation_errors.append(f"{key}: {', '.join(allowed_values)} 중 하나여야 합니다.")
                            elif schema_type == 'str':
                                if not isinstance(value, str):
                                    validation_errors.append(f"{key}: 문자열이어야 합니다.")
                            elif schema_type == 'match':
                                if not isinstance(value, str):
                                    validation_errors.append(f"{key}: 문자열이어야 합니다.")
                                else:
                                    # match(정규식) 형식에서 정규식 추출
                                    pattern = field_schema.split('(')[1].rstrip('?)').rstrip(')')
                                    import re
                                    if not re.match(pattern, value):
                                        validation_errors.append(f"{key}: 올바른 형식이 아닙니다. (형식: {pattern})")
                                    

                if validation_errors:
                    return jsonify({
                        'success': False,
                        'error': '유효성 검사 실패',
                        'details': validation_errors
                    }), 400

                try:
                    # 현재 설정과 새로운 설정을 병합
                    updated_options = current_options.copy()
                    updated_options.update(data)

                    # API 호출을 위한 헤더와 데이터 준비
                    headers = {
                        'Authorization': f'Bearer {os.environ.get("SUPERVISOR_TOKEN", "")}',
                        'Content-Type': 'application/json'
                    }
                    api_data = {
                        'options': updated_options
                    }

                    # Supervisor API 호출
                    response = requests.post(
                        'http://supervisor/addons/self/options',
                        headers=headers,
                        json=api_data
                    )

                    if response.status_code != 200:
                        return jsonify({
                            'success': False,
                            'error': f'설정 저장 실패: {response.text}'
                        }), 500

                    # 애드온 재시작 요청
                    restart_response = requests.post(
                        'http://supervisor/addons/self/restart',
                        headers=headers
                    )

                    if restart_response.status_code != 200:
                        return jsonify({
                            'success': False,
                            'error': f'애드온 재시작 실패: {restart_response.text}'
                        }), 500
                    #전달되지 못할 response..
                    return jsonify({'success': True, 'message': '설정이 저장되었습니다. 애드온을 재시작합니다.'})

                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/recent_messages')
        def get_recent_messages():
            """최근 MQTT 메시지 목록을 제공합니다."""
            return jsonify({
                'messages': self.recent_messages[-100:]  # 최근 100개 메시지만 반환
            })

        @self.app.route('/api/packet_logs')
        def get_packet_logs():
            """패킷 로그를 제공합니다."""
            try:
                send_packets = []
                recv_packets = []

                # 가능한 패킷 타입
                packet_types = ['command', 'state_request', 'state', 'ack']

                # 송신 패킷 처리
                for packet in self.wallpad_controller.COLLECTDATA['send_data']:
                    packet_info = {
                        'packet': packet,
                        'results': []
                    }
                    for packet_type in packet_types:
                        device_info = self._analyze_packet_structure(packet, packet_type)
                        if device_info['success']:
                            packet_info['results'].append({
                                'device': device_info['device'],
                                'packet_type': packet_type
                            })
                    
                    # 분석 결과가 없는 경우 Unknown으로 처리
                    if not packet_info['results']:
                        packet_info['results'].append({
                            'device': 'Unknown',
                            'packet_type': 'Unknown'
                        })

                    send_packets.append(packet_info)

                # 수신 패킷 처리 (송신 패킷 처리와 동일한 로직 적용)
                for packet in self.wallpad_controller.COLLECTDATA['recv_data']:
                    packet_info = {
                        'packet': packet,
                        'results': []
                    }
                    for packet_type in packet_types:
                        device_info = self._analyze_packet_structure(packet, packet_type)
                        if device_info['success']:
                            packet_info['results'].append({
                                'device': device_info['device'],
                                'packet_type': packet_type
                            })

                    # 분석 결과가 없는 경우 Unknown으로 처리
                    if not packet_info['results']:
                        packet_info['results'].append({
                            'device': 'Unknown',
                            'packet_type': 'Unknown'
                        })

                    recv_packets.append(packet_info)

                return jsonify({
                    'send': send_packets,
                    'recv': recv_packets
                })

            except Exception as e:
                return jsonify({
                    'error': str(e)
                }), 500

        @self.app.route('/api/find_devices', methods=['POST'])
        def find_devices():
            try:
                # 기존 기기 목록 파일 삭제
                if os.path.exists('/share/commax_found_device.json'):
                    os.remove('/share/commax_found_device.json')
                
                # Supervisor API를 통해 애드온 재시작
                headers = {
                    'Authorization': f'Bearer {os.environ.get("SUPERVISOR_TOKEN", "")}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(
                    'http://supervisor/addons/self/restart',
                    headers=headers
                )

                if response.status_code != 200:
                    return jsonify({
                        'success': False,
                        'error': f'애드온 재시작 실패: {response.text}'
                    }), 500
                # 전달되지 못할 response..
                return jsonify({'success': True})

            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/analyze_packet', methods=['POST'])
        def analyze_packet():
            try:
                data = request.get_json()
                command = data.get('command', '').strip()
                packet_type = data.get('type', 'command')  # 'command' 또는 'state'

                # 체크섬 계산
                checksum_result = checksum(command)

                # 패킷 구조 분석
                analysis_result = self._analyze_packet_structure(command, packet_type)

                if not analysis_result["success"]:
                    return jsonify(analysis_result), 400

                response = {
                    "success": True,
                    "device": analysis_result["device"],
                    "analysis": analysis_result["analysis"],
                    "checksum": checksum_result
                }

                # command 패킷 경우 예상 상태 패킷 추가
                if packet_type == 'command' and checksum_result:
                    expected_state = self.wallpad_controller.generate_expected_state_packet(checksum_result)
                    if expected_state:
                        response["expected_state"] = {
                            "required_bytes": expected_state["required_bytes"],
                            "possible_values": expected_state["possible_values"]
                        }

                return jsonify(response)

            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 400

        @self.app.route('/api/packet_structures')
        def get_packet_structures():
            structures = {}
            for device_name, device in self.wallpad_controller.DEVICE_STRUCTURE.items():
                structures[device_name] = {
                    "type": device['type'],
                    "command": self._get_packet_structure(device_name, device, 'command'),
                    "state": self._get_packet_structure(device_name, device, 'state'),
                    "state_request": self._get_packet_structure(device_name, device, 'state_request'),
                    "ack": self._get_packet_structure(device_name, device, 'ack')
                }
             
            return jsonify(structures)

        @self.app.route('/api/packet_suggestions')
        def get_packet_suggestions():
            """패킷 입력 도우미를 위한 정보를 제공합니다."""
            suggestions = {
                'headers': {},  # 헤더 정보
                'values': {}    # 각 바이트 위치별 가능한 값
            }
            
            # 명령 패킷 헤더
            command_headers = []
            for device_name, device in self.wallpad_controller.DEVICE_STRUCTURE.items():
                if 'command' in device:
                    command_headers.append({
                        'header': device['command']['header'],
                        'device': device_name
                    })
            suggestions['headers']['command'] = command_headers
            
            # 상태 패킷 헤더
            state_headers = []
            for device_name, device in self.wallpad_controller.DEVICE_STRUCTURE.items():
                if 'state' in device:
                    state_headers.append({
                        'header': device['state']['header'],
                        'device': device_name
                    })
            suggestions['headers']['state'] = state_headers
            
            # 상태 요청 패킷 헤더
            state_request_headers = []
            for device_name, device in self.wallpad_controller.DEVICE_STRUCTURE.items():
                if 'state_request' in device:
                    state_request_headers.append({
                        'header': device['state_request']['header'],
                        'device': device_name
                    })
            suggestions['headers']['state_request'] = state_request_headers
            
            # 응답 패킷 헤더
            ack_headers = []
            for device_name, device in self.wallpad_controller.DEVICE_STRUCTURE.items():
                if 'ack' in device:
                    ack_headers.append({
                        'header': device['ack']['header'],
                        'device': device_name
                    })
            suggestions['headers']['ack'] = ack_headers
            
            # 각 기기별 가능한 값들
            for device_name, device in self.wallpad_controller.DEVICE_STRUCTURE.items():
                for packet_type in ['command', 'state', 'state_request', 'ack']:
                    if packet_type in device:
                        key = f"{device_name}_{packet_type}"
                        suggestions['values'][key] = {}
                        
                        for pos, field in device[packet_type]['structure'].items():
                            if 'values' in field:
                                suggestions['values'][key][pos] = {
                                    'name': field['name'],
                                    'values': field['values']
                                }
            
            return jsonify(suggestions)

        @self.app.route('/api/send_packet', methods=['POST'])
        def send_packet():
            try:
                data = request.get_json()
                packet = data.get('packet', '').strip()
                
                if not packet:
                    return jsonify({"success": False, "error": "패킷이 비어있습니다."}), 400
                
                # 패킷 체크섬 검증
                if packet != checksum(packet):
                    return jsonify({"success": False, "error": "잘못된 패킷입니다."}), 400
                
                # 패킷을 bytes로 변환하여 MQTT로 발행
                packet_bytes = bytes.fromhex(packet)
                self.wallpad_controller.publish_mqtt(f'{self.wallpad_controller.ELFIN_TOPIC}/send', packet_bytes)
                
                return jsonify({"success": True})
            
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route('/api/custom_packet_structure', methods=['GET'])
        def get_custom_packet_structure():
            """커스텀 패킷 구조 파일의 내용을 반환합니다."""
            try:
                custom_file = '/share/packet_structures_custom.yaml'
                if os.path.exists(custom_file):
                    with open(custom_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                else:
                    # 기본 패킷 구조 파일 읽기
                    with open('/apps/packet_structures_commax.yaml', 'r', encoding='utf-8') as f:
                        content = f.read()
                return jsonify({'content': content, 'success': True})
            except Exception as e:
                return jsonify({'error': str(e), 'success': False})

        @self.app.route('/api/custom_packet_structure', methods=['POST'])
        def save_custom_packet_structure():
            """커스텀 패킷 구조 파일을 저장합니다."""
            try:
                content = request.json.get('content', '')
                
                # YAML 유효성 검사
                try:
                    yaml.safe_load(content)
                except yaml.YAMLError as e:
                    return jsonify({'error': f'YAML 형식이 잘못되었습니다: {str(e)}', 'success': False})

                # 백업 생성
                backup_dir = '/share/packet_structure_backups'
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                
                custom_file = '/share/packet_structures_custom.yaml'
                if os.path.exists(custom_file):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_file = f'{backup_dir}/packet_structures_custom_{timestamp}.yaml'
                    shutil.copy2(custom_file, backup_file)

                # 새 내용 저장
                with open(custom_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e), 'success': False})

    def _get_editable_fields(self, packet_data):
        """패킷 구조에서 편집 가능한 필드만 추출합니다."""
        if not packet_data:
            return {}
            
        result = {
            'header': packet_data.get('header', ''),
            'structure': {}
        }
        
        if 'structure' in packet_data:
            for position, field in packet_data['structure'].items():
                result['structure'][position] = {
                    'name': field.get('name', ''),
                    'values': field.get('values', {})
                }
                
        return result

    def _merge_packet_structure(self, current, new):
        """현재 패킷 구조와 새로운 패킷 구조를 병합합니다."""
        if 'header' in new:
            current['header'] = new['header']
            
        if 'structure' in new:
            if 'structure' not in current:
                current['structure'] = {}
                
            for position, field in new['structure'].items():
                if position not in current['structure']:
                    current['structure'][position] = {}
                    
                current['structure'][position]['name'] = field.get('name', '')
                current['structure'][position]['values'] = field.get('values', {})

    def _analyze_packet_structure(self, command: str, packet_type: str) -> Dict[str, Any]:
        """패킷 구조를 분석하고 관련 정보를 반환합니다."""
        # 헤더 기기 찾기
        header = command[:2]
        device_info = None
        device_name = None

        for name, device in self.wallpad_controller.DEVICE_STRUCTURE.items():
            if packet_type in device and device[packet_type]['header'] == header:
                device_info = device[packet_type]
                device_name = name
                break

        if not device_info:
            return {
                "success": False,
                "error": f"알 수 없는 패킷입니다."
            }

        # 각 바이트 분석
        byte_analysis = []
        # 헤더 추가
        byte_analysis.append(f"Byte 0: header = {device_name} {packet_type} ({header})")

        for pos, field in device_info['structure'].items():
            pos = int(pos)
            if pos * 2 + 2 <= len(command):
                byte_value = command[pos*2:pos*2+2]
                desc = f"Byte {pos}: {field['name']}"

                if field['name'] == 'empty':
                    desc = f"Byte {pos}: (00)"
                elif field['name'] == 'checksum':
                    desc = f"Byte {pos}: 체크섬"
                elif 'values' in field:
                    # 알려진 값과 매칭
                    matched_value = None
                    for key, value in field['values'].items():
                        if value == byte_value:
                            matched_value = key
                            break
                    if matched_value:
                        desc += f" = {matched_value} ({byte_value})"
                    else:
                        desc += f" = {byte_value}"
                else:
                    desc += f" = {byte_value}"

                byte_analysis.append(desc)

        return {
            "success": True,
            "device": device_name,
            "analysis": byte_analysis
        }

    def _get_packet_structure(self, device_name: str, device: Dict[str, Any], packet_type: str) -> Dict[str, Any]:
        """패킷 구조 정보를 생성합니다."""
        if packet_type not in device:
            return {}

        structure = device[packet_type]
        byte_desc = {}
        byte_values = {}
        byte_memos = {}  # memo 정보를 저장할 딕셔너리
        examples = []

        # 헤더 설명
        byte_desc[0] = f"header ({structure['header']})"
        
        # 각 바이트 설명과 값 생성
        for pos, field in structure['structure'].items():
            pos = int(pos)
            if field['name'] == 'empty':
                byte_desc[pos] = "00"
            else:
                byte_desc[pos] = field['name']
                if 'values' in field:
                    byte_values[pos] = field['values']
                if 'memo' in field:  # memo 필드가 있는 경우 저장
                    byte_memos[pos] = field['memo']

        # # 예시 패킷 동적 생성
        # if device['type'] == 'Thermo':
        #     if packet_type == 'command':
        #         # 온도조절기 켜기
        #         packet = list('00' * 7)  # 7바이트 초기화
        #         packet[0] = structure['header']  # 헤더
        #         packet[1] = '01'  # 1번 온도조절기
        #         packet[2] = '04'  # 전원
        #         packet[3] = '81'  # ON
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 온도조절기 켜기"
        #         })
                
        #         # 온도 설정
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 온도조절기
        #         packet[2] = '03'  # 온도 설정
        #         packet[3] = '18'  # 24도
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 온도조절기 온도 24도로 설정"
        #         })
        #     elif packet_type == 'state':
        #         # 대기 상태
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '81'  # 상태
        #         packet[2] = '01'  # 1번 온도조절기
        #         packet[3] = '18'  # 24도
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 온도조절기 대기 상태 (현재 24도, 설정 24도)"
        #         })
                
        #         # 난방 중
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '83'  # 난방
        #         packet[2] = '01'  # 1번 온도조절기
        #         packet[3] = '18'  # 24도
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 온도조절기 난방 중 (현재 24도, 설정 24도)"
        #         })
        #     elif packet_type == 'state_request':
        #         # 상태 요청
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 온도조절기
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 온도조절기 상태 요청"
        #         })
        #     elif packet_type == 'ack':
        #         # 상태 요청
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 온도조절기
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 온도조절기 상태 요청"
        #         })
                
        # elif device['type'] == 'Light':
        #     if packet_type == 'command':
        #         # 조명 끄기
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 조명
        #         packet[2] = '00'  # OFF
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 조명 끄기"
        #         })
                
        #         # 조명 켜기
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 조명
        #         packet[2] = '01'  # ON
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 조명 켜기"
        #         })
        #     elif packet_type == 'state':
        #         # 조명 꺼짐
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '00'  # OFF
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 조명 꺼짐"
        #         })
                
        #         # 조명 켜짐
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # ON
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 조명 켜짐"
        #         })
        #     elif packet_type == 'state_request':
        #         # 상태 요청
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 조명
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 조명 상태 요청"
        #         })
        #     elif packet_type == 'ack':
        #         # 상태 요청
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 조명
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 조명 상태 요청"
        #         })
                
        # elif device['type'] == 'Fan':
        #     if packet_type == 'command':
        #         # 환기장치 켜기
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 환기장치
        #         packet[2] = '01'  # 전원
        #         packet[3] = '04'  # ON
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 환기장치 켜기"
        #         })
                
        #         # 환기장치 약으로 설정
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 환기장치
        #         packet[2] = '02'  # 풍량
        #         packet[3] = '00'  # 약(low)
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 환기장치 약(low)으로 설정"
        #         })
        #     elif packet_type == 'state':
        #         # 환기장치 켜짐 (약)
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '04'  # ON
        #         packet[2] = '01'  # 1번 환기장치
        #         packet[3] = '00'  # 약(low)
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 환기장치 켜짐 (약)"
        #         })
                
        #         # 환기장치 꺼짐
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 환기장치 꺼짐"
        #         })
        #     elif packet_type == 'state_request':
        #         # 상태 요청
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 환기장치
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 환기장치 상태 요청"
        #         })
        #     elif packet_type == 'ack':
        #         # 상태 요청
        #         packet = list('00' * 7)
        #         packet[0] = structure['header']
        #         packet[1] = '01'  # 1번 환기장치
        #         examples.append({
        #             "packet": ''.join(packet),
        #             "desc": "1번 환기장치 상태 요청"
        #         })
        
        return {
            "header": structure['header'],
            "byte_desc": byte_desc,
            "byte_values": byte_values,
            "byte_memos": byte_memos,  # memo 정보 추가
            # "examples": examples
        }

    def _get_device_info(self, packet: str) -> Dict[str, str]:
        """패킷의 헤더를 기반으로 기기 정보를 반환합니다."""
        if len(packet) < 2:
            return {"name": "Unknown", "packet_type": "Unknown"}
            
        header = packet[:2]
        
        # 명령 패킷 확인
        for device_name, device in self.wallpad_controller.DEVICE_STRUCTURE.items():
            if 'command' in device and device['command']['header'] == header:
                return {"name": device_name, "packet_type": "Command"}
                
        # 상태 패킷 확인
        for device_name, device in self.wallpad_controller.DEVICE_STRUCTURE.items():
            if 'state' in device and device['state']['header'] == header:
                return {"name": device_name, "packet_type": "State"}
                
        return {"name": "Unknown", "packet_type": "Unknown"}

    def add_mqtt_message(self, topic: str, payload: str) -> None:
        """MQTT 메시지를 최근 메시지 목록에 추가합니다."""
        self.recent_messages.append({
            'topic': topic,
            'payload': payload,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        })
        # 최근 100개 메시지만 유지
        if len(self.recent_messages) > 100:
            self.recent_messages = self.recent_messages[-100:] 

    def run(self):
        # Flask 서버 실행 (with WebSocket support)
        self.server = WSGIServer(('0.0.0.0', 8099), self.app,
                               handler_class=WebSocketHandler)

        # 별도의 스레드에서 서버 실행
        threading.Thread(target=self._run_server, daemon=True).start()
        
    def _run_server(self):
        try:
            self.server.serve_forever()
        except Exception as e:
            print(f"Server error: {e}")

    def stop(self):
        if self.server:
            self.server.stop()
            self.server = None 