import serial
import struct
import time
import binascii

def receive_split(receive_buffer):
    """Splits the hex string into 2-character bytes."""
    buff = []
    for i in range(0, len(receive_buffer), 2):
        buff.append(receive_buffer[i:i + 2])
    return buff

def hex_to_ieee(length, buff):
    """Converts the raw hex buffer into IEEE-754 floating point numbers."""
    data = []
    # Logic matches the original manufacturer's parsing offsets
    # range(start, stop, step)
    for i in range(length // 2 - 3, 11, -4):
        hex_str = ""
        for j in range(i, i - 4, -1):
            hex_str += buff[j]
        
        # Convert hex string to float
        float_val = struct.unpack('>f', binascii.unhexlify(hex_str))[0]
        data.append(float_val)
    
    data.reverse()
    return data

def main():
    # --- CONFIGURATION ---
    # Based on your previous output, ensure this is COM3. 
    # The A9 specifically requires 921600 baud.
    port = '/dev/ttyUSB0' 
    baudrate = 921600 

    try:
        hf_imu = serial.Serial(port=port, baudrate=baudrate, timeout=0.5)
        if hf_imu.is_open:
            print(f"Success: Connected to IMU on {port}")
        else:
            hf_imu.open()
            print(f"Opened port {port}")
    except Exception as e:
        print(f"Error: Could not connect to {port}. Check your USB connection.")
        print(f"Details: {e}")
        return

    # Initialize data containers
    sensor_data = [0] * 11 
    
    print("Starting data stream...\n")

    while True:
        try:
            count = hf_imu.in_waiting
            if count > 24:
                # Read raw bytes and convert to hex string
                raw_bytes = hf_imu.read(count)
                receive_buffer = raw_bytes.hex()
                receive_len = len(receive_buffer)
                buff = receive_split(receive_buffer)

                # Check for Header: aa 55 (Sync) and 2c (Data Type)
                if buff[0] + buff[1] + buff[2] == 'aa552c':
                    sensor_data = hex_to_ieee(receive_len, buff)

                # Check for Header: aa 55 (Sync) and 14 (Angle Type)
                if buff[0] + buff[1] + buff[2] == 'aa5514':
                    rpy = hex_to_ieee(receive_len, buff)

                    # --- Display Results ---
                    print("-" * 30)
                    print(f"Acceleration (g):  X: {sensor_data[3]:.2f}  Y: {sensor_data[4]:.2f}  Z: {sensor_data[5]:.2f}")
                    
                    # Converting to rad/s (using original formula: value * -9.8)
                    print(f"Angular Vel (rad/s): X: {sensor_data[0]*-9.8:.2f}  Y: {sensor_data[1]*-9.8:.2f}  Z: {sensor_data[2]*-9.8:.2f}")

                    # Euler Angles
                    print(f"Angles (deg):      Roll: {rpy[0]:.2f}  Pitch: {-rpy[1]:.2f}  Yaw: {-rpy[2]+180:.2f}")

                    # Magnetometer
                    print(f"Magnetic (mG):     X: {sensor_data[6]*1000:.0f}  Y: {sensor_data[7]*1000:.0f}  Z: {sensor_data[8]*1000:.0f}")

            time.sleep(0.001)

        except KeyboardInterrupt:
            hf_imu.close()
            print("\nConnection closed by user.")
            break
        except Exception as e:
            print(f"Data Error: {e}")
            break

if __name__ == "__main__":
    main()