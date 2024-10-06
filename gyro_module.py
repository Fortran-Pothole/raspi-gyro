import smbus2 as smbus
import time

# I2C 설정
bus = smbus.SMBus(1)
MPU6050_ADDR = 0x68

# MPU6050 레지스터 주소
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
MS_TO_KMH = 3.6

# 가속도 스케일링 상수 및 감속 설정
ACCEL_SCALE_MODIFIER = 16384.0  # 2g 모드에서 스케일링 상수
GRAVITY_MS2 = 9.81  # 중력 가속도 (m/s²)
ACCEL_SCALE_FACTOR = 1.5  # 가속도 배율
MIN_DECELERATION_FACTOR = 0.95  # 미세한 감속 비율
MAX_CHANGE_KMH = 60  # 최대 속도 변화량 (km/h)
BASE_SPEED_KMH = 0  # 기본 속도 (km/h)
MAX_SPEED_KMH = BASE_SPEED_KMH + MAX_CHANGE_KMH

# MPU6050 초기화
bus.write_byte_data(MPU6050_ADDR, PWR_MGMT_1, 0)

# 영점 조정
def calibrate_gyro():
    x_offset, y_offset, z_offset = 0, 0, 0
    for _ in range(100):
        x, y, z = read_raw_accel()
        x_offset += x
        y_offset += y
        z_offset += z
        time.sleep(0.01)
    return x_offset / 100, y_offset / 100, z_offset / 100

# 가속도 데이터 읽기 (원시 값)
def read_raw_accel():
    accel_x = bus.read_byte_data(MPU6050_ADDR, ACCEL_XOUT_H) << 8 | bus.read_byte_data(MPU6050_ADDR, ACCEL_XOUT_H+1)
    accel_y = bus.read_byte_data(MPU6050_ADDR, ACCEL_XOUT_H+2) << 8 | bus.read_byte_data(MPU6050_ADDR, ACCEL_XOUT_H+3)
    accel_z = bus.read_byte_data(MPU6050_ADDR, ACCEL_XOUT_H+4) << 8 | bus.read_byte_data(MPU6050_ADDR, ACCEL_XOUT_H+5)

    # 음수 보정
    if accel_x >= 0x8000:
        accel_x = -((65535 - accel_x) + 1)
    if accel_y >= 0x8000:
        accel_y = -((65535 - accel_y) + 1)
    if accel_z >= 0x8000:
        accel_z = -((65535 - accel_z) + 1)

    return accel_x, accel_y, accel_z

# 가속도 데이터 읽기 (스케일링 및 영점 조정 후, Y축만 사용)
def read_accel_y(y_offset):
    raw_x, raw_y, raw_z = read_raw_accel()
    accel_y = ((raw_y - y_offset) / ACCEL_SCALE_MODIFIER) * GRAVITY_MS2  # m/s²로 변환
    accel_y *= ACCEL_SCALE_FACTOR  # 가속도 배율 적용
    return accel_y

# 속도 변화량을 반환하는 함수
def get_velocity():
    # 영점 조정 수행
    _, y_offset, _ = calibrate_gyro()

    prev_accel_y = 0
    velocity_y_change = 0

    prev_time = time.time()

    while True:
        current_time = time.time()
        dt = current_time - prev_time
        prev_time = current_time

        # Y축 가속도 데이터 읽기
        accel_y = read_accel_y(y_offset)

        # 가속도 변화량 계산
        accel_change = abs(accel_y - prev_accel_y)
        prev_accel_y = accel_y

        # 가속도 변화량이 클수록 더 빠르게 속도 변화
        if abs(accel_y) > 0.05:
            velocity_y_change += accel_y * (accel_change + 1) * dt
        else:
            velocity_y_change *= MIN_DECELERATION_FACTOR

        # 속도 변화량 제한
        if velocity_y_change * MS_TO_KMH > MAX_CHANGE_KMH:
            velocity_y_change = MAX_CHANGE_KMH / MS_TO_KMH

        # 최종 속도 계산
        total_velocity_kmh = BASE_SPEED_KMH + velocity_y_change * MS_TO_KMH
        if total_velocity_kmh > MAX_SPEED_KMH:
            total_velocity_kmh = MAX_SPEED_KMH

        # 속도가 0 이하로 내려가지 않도록 설정
        if total_velocity_kmh < 0:
            total_velocity_kmh = 0

        #if total_velocity_kmh > 0 and total_velocity_kmh < 1:
        #    total_velocity_kmh = 0


        yield total_velocity_kmh
        time.sleep(0.3)