'pip install pyserial'
'this one is for linux/mac get the windows from: https://github.com/belovictor/handsfree_ros_imu/tree/master/demo/linux'

import serial
import struct
import platform
import serial.tools.list_ports
import math


# Find ttyUSB* devices (IMU serial ports)
def find_ttyUSB():
    print(
        "The default IMU serial port is /dev/ttyUSB0. "
        "If multiple serial devices are detected, please modify the IMU port in the launch file."
    )
    ports = [port.device for port in serial.tools.list_ports.comports() if 'USB' in port.device]
    print(
        "Currently connected {} serial devices ({}): {}".format(
            'USB', len(ports), ports
        )
    )


# CRC checksum verification (CRC-16)
def checkSum(list_data, check_data):
    data = bytearray(list_data)
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if (crc & 1) != 0:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return hex(((crc & 0xff) << 8) + (crc >> 8)) == hex(check_data[0] << 8 | check_data[1])


# Convert hexadecimal byte data to IEEE 754 floating-point numbers
def hex_to_ieee(raw_data):
    ieee_data = []
    raw_data.reverse()

    for i in range(0, len(raw_data), 4):
        hex_str = (
            hex(raw_data[i]     | 0xff00)[4:6] +
            hex(raw_data[i + 1] | 0xff00)[4:6] +
            hex(raw_data[i + 2] | 0xff00)[4:6] +
            hex(raw_data[i + 3] | 0xff00)[4:6]
        )

        if python_version == '2':
            ieee_data.append(struct.unpack('>f', hex_str.decode('hex'))[0])
        elif python_version == '3':
            ieee_data.append(struct.unpack('>f', bytes.fromhex(hex_str))[0])

    ieee_data.reverse()
    return ieee_data


# Process incoming serial data byte-by-byte
def handleSerialData(raw_data):
    global buff, key, angle_degree, magnetometer, acceleration, angularVelocity, pub_flag

    # Store byte depending on Python version
    if python_version == '2':
        buff[key] = ord(raw_data)
    else:
        buff[key] = raw_data

    key += 1

    # Check packet header
    if buff[0] != 0xAA:
        key = 0
        return

    if key < 3:
        return

    if buff[1] != 0x55:
        key = 0
        return

    # Wait until full packet length is received
    if key < buff[2] + 5:
        return

    # Full packet received
    data_buff = list(buff.values())

    # IMU data packet (gyro, accel, magnetometer)
    if buff[2] == 0x2C and pub_flag[0]:
        if checkSum(data_buff[2:47], data_buff[47:49]):
            data = hex_to_ieee(data_buff[7:47])
            angularVelocity = data[1:4]
            acceleration = data[4:7]
            magnetometer = data[7:10]
        else:
            print("Checksum failed")
        pub_flag[0] = False

    # Euler angle packet
    elif buff[2] == 0x14 and pub_flag[1]:
        if checkSum(data_buff[2:23], data_buff[23:25]):
            data = hex_to_ieee(data_buff[7:23])
            angle_degree = data[1:4]
        else:
            print("Checksum failed")
        pub_flag[1] = False

    else:
        print("No parser implemented for packet length:", buff[2])
        print("Or invalid data")
        buff = {}
        key = 0
        return

    buff = {}
    key = 0

    # Wait until both packets are received
    if pub_flag[0] or pub_flag[1]:
        return

    pub_flag[0] = pub_flag[1] = True

    # Normalize acceleration to gravity direction
    acc_norm = math.sqrt(
        acceleration[0] ** 2 +
        acceleration[1] ** 2 +
        acceleration[2] ** 2
    )
    
    print("\033[2J", end="")   # Clear screen once
    
    print("\033[H", end="")
    
    c = (f"""
Acceleration (m/s²):
    x-axis: {acceleration[0] * -9.8 / acc_norm:.2f}
    y-axis: {acceleration[1] * -9.8 / acc_norm:.2f}
    z-axis: {acceleration[2] * -9.8 / acc_norm:.2f}

Angular Velocity (rad/s):
    x-axis: {angularVelocity[0]:.2f}
    y-axis: {angularVelocity[1]:.2f}
    z-axis: {angularVelocity[2]:.2f}

Euler Angles (degrees):
    roll : {angle_degree[0]:.2f}
    pitch: {angle_degree[1]:.2f}
    yaw  : {angle_degree[2]:.2f}

Magnetic Field:
    x-axis: {magnetometer[0]:.2f}
    y-axis: {magnetometer[1]:.2f}
    z-axis: {magnetometer[2]:.2f}
""")
    print(c, end = '\r', flush=True)


# Global variables
key = 0
buff = {}
angularVelocity = [0, 0, 0]
acceleration = [0, 0, 0]
magnetometer = [0, 0, 0]
angle_degree = [0, 0, 0]
pub_flag = [True, True]


if __name__ == "__main__":
    python_version = platform.python_version()[0]

    find_ttyUSB()

    port = "/dev/ttyUSB0"
    baudrate = 921600

    try:
        hf_imu = serial.Serial(port=port, baudrate=baudrate, timeout=0.5)
        if hf_imu.isOpen():
            print("Serial port opened successfully...")
        else:
            hf_imu.open()
            print("Serial port opened successfully...")
    except Exception as e:
        print(e)
        print("Failed to open serial port")
        exit(0)

    while True:
        try:
            byte_count = hf_imu.inWaiting()
        except Exception as e:
            print("Exception:", e)
            print("IMU disconnected or communication error")
            exit(0)

        if byte_count > 0:
            data = hf_imu.read(byte_count)
            for byte in data:
                handleSerialData(byte)
