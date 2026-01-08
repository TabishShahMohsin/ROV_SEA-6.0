import serial.tools.list_ports

def get_imu_port():
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        # Check for common IMU/USB-Serial keywords in the description
        # For HFI-A9, it usually shows up as 'CH340', 'CP210', or 'USB Serial'
        desc = port.description.lower()
        if "usb" in desc or "serial" in desc or "ch340" in desc:
            print(f"Found IMU on port: {port.device} ({port.description})")
            return port.device
            
    return None

# Usage
port_name = get_imu_port()

if port_name:
    print(f"Connecting to {port_name}...")
    # ser = serial.Serial(port_name, 921600)
else:
    print("No IMU detected. Check your USB connection.")