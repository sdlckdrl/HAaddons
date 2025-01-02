import logging
import sys

class Logger:
    def __init__(self, debug=False, elfin_log=False, mqtt_log=False):
        # 로거 생성
        self.logger = logging.getLogger('ComMaxWallpad')
        if debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        
        # 포맷터 설정
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %p %I:%M:%S'
        )
        
        # 스트림 핸들러 설정 (stderr로 출력)
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)
        
        # 로그 레벨 설정을 위한 플래그 저장
        self.enable_elfin_log = elfin_log
        self.enable_mqtt_log = mqtt_log

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def warning(self, message):
        self.logger.warning(message)

    def debug(self, message):
        self.logger.debug(message)

    def signal(self, message):
        if self.enable_elfin_log:
            self.logger.debug(f'[RS485] {message}')

    def mqtt(self, message):
        if self.enable_mqtt_log:
            self.logger.debug(f'[MQTT] {message}')
