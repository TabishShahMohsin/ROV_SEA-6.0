import serial
import struct
import platform
import serial.tools.list_ports
import threading
import time

class IMU:
    def __init__(self, port="/dev/ttyUSB0", baudrate=921600):
        self.port = port
        self.baudrate = baudrate
        self.python_version = platform.python_version()[0]
        
        # State variables
        self.key = 0
        self.buff = {}
        self.angle_degree = [0, 0, 0] # [roll, pitch, yaw]
        self.pub_flag = [True, True]
        self.running = False
        self.ser = None

    def checkSum(self, list_data, check_data):
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

    def hex_to_ieee(self, raw_data):
        ieee_data = []
        raw_data.reverse()
        for i in range(0, len(raw_data), 4):
            hex_str = (
                hex(raw_data[i]     | 0xff00)[4:6] +
                hex(raw_data[i + 1] | 0xff00)[4:6] +
                hex(raw_data[i + 2] | 0xff00)[4:6] +
                hex(raw_data[i + 3] | 0xff00)[4:6]
            )
            if self.python_version == '2':
                ieee_data.append(struct.unpack('>f', hex_str.decode('hex'))[0])
            else:
                ieee_data.append(struct.unpack('>f', bytes.fromhex(hex_str))[0])
        ieee_data.reverse()
        return ieee_data

    def handleSerialData(self, raw_data):
        if self.python_version == '2':
            self.buff[self.key] = ord(raw_data)
        else:
            self.buff[self.key] = raw_data

        self.key += 1

        if self.buff[0] != 0xAA:
            self.key = 0
            return
        if self.key < 3: return
        if self.buff[1] != 0x55:
            self.key = 0
            return
        if self.key < self.buff[2] + 5: return

        data_buff = list(self.buff.values())

        # Euler angle packet
        if self.buff[2] == 0x14:
            if self.checkSum(data_buff[2:23], data_buff[23:25]):
                data = self.hex_to_ieee(data_buff[7:23])
                self.angle_degree = data[1:4]
            self.pub_flag[1] = False
        
        # Other packets (0x2C) - we just acknowledge them to keep sync
        elif self.buff[2] == 0x2C:
            self.pub_flag[0] = False

        self.buff = {}
        self.key = 0
        if not self.pub_flag[0] and not self.pub_flag[1]:
            self.pub_flag[0] = self.pub_flag[1] = True

    def _read_loop(self):
        while self.running:
            try:
                if self.ser.inWaiting() > 0:
                    data = self.ser.read(self.ser.inWaiting())
                    for byte in data:
                        self.handleSerialData(byte)
            except Exception as e:
                print(f"IMU Read Error: {e}")
                break
            time.sleep(0.001)

    def start(self):
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=0.5)
            self.running = True
            threading.Thread(target=self._read_loop, daemon=True).start()
            return True
        except Exception as e:
            print(f"Failed to open IMU: {e}")
            return False

    def get_angles(self):
        """Returns (roll, pitch, yaw)"""
        return self.angle_degree[0], self.angle_degree[1], self.angle_degree[2]