import stomp
import time
import logging
import socket
from gyro_module import get_velocity
import json
# 로그 설정
logging.basicConfig(
    filename='stomp_client_connection.log',  # 연결 관련 로그 파일
    level=logging.INFO,           # 로그 레벨 설정
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 데이터 전송 로그 파일 별도 설정
data_logger = logging.getLogger('data_logger')
data_logger.setLevel(logging.INFO)
data_handler = logging.FileHandler('stomp_client_data.log')  # 데이터 전송 로그 파일
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
data_handler.setFormatter(formatter)
data_logger.addHandler(data_handler)

# STOMP 설정
class MyListener(stomp.ConnectionListener):
    def on_error(self, headers, message):
        logging.error(f'Error: {message}')

    def on_message(self, headers, message):
        logging.info(f'Received message: {message}')

    def on_disconnected(self):
        logging.warning("서버와의 연결이 끊어졌습니다.")
        self.connected = False

listener = MyListener()
listener.connected = True  # 연결 상태 플래그

# STOMP 연결 시작 함수 정의
def connect_stomp():
    conn = stomp.Connection([('15.164.200.30', 61613)], heartbeats=(5000, 5000))
    conn.set_listener('', listener)
    try:
        # timeout을 설정하여 일정 시간 내에 연결이 되지 않으면 오류 발생
        conn.connect(login='admin', passcode='admin', wait=True, timeout=10)
        listener.connected = True
        logging.info("서버와 연결되었습니다.")
    except (socket.timeout, Exception) as e:
        logging.error(f"연결 중 오류 발생: {e}")
        listener.connected = False
    return conn

conn = connect_stomp()

# gyro_module로부터 속도 데이터를 받아서 STOMP로 전송
velocity_generator = get_velocity()

try:
    while True:
        if listener.connected:
            for velocity in velocity_generator:
                try:
                    # 연결 상태를 별도로 ping으로 확인하는 로직 추가 가능
                    if not conn.is_connected():
                        raise Exception("STOMP 서버에 연결되지 않았습니다.")
                    
                    # JSON 형식으로 메시

                    headers = {"content-type": "application/json"}
                    rounded_velocity = round(velocity)  # 소숫점 둘째 자리까지 반올림
                    message = json.dumps({"velocity": rounded_velocity})
                    conn.send(body=message, destination='/app/sendKmH', headers=headers)
                    data_logger.info(f"속도 데이터 전송: {rounded_velocity} km/h")
                    print(f"속도 데이터 전송: {rounded_velocity} km/h")
                except Exception as e:
                    logging.error(f"메시지 전송 중 오류 발생: {e}")
                    listener.connected = False
                    break
                time.sleep(0.3)
        else:
            # 연결이 끊어졌으면 재연결 시도
            logging.info("재연결 시도 중...")
            print("재연결 시도 중...")
            conn = connect_stomp()
            time.sleep(5)

except KeyboardInterrupt:
    logging.info("연결 종료")
    print("연결 종료")
finally:
    if conn.is_connected():
        conn.disconnect()
        logging.info("STOMP 연결이 종료되었습니다.")