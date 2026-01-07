# sudo apt-get install python-smbus2
# pip install ms5837
# git clone https://github.com/bluerobotics/ms5837-python

import ms5837 
import time

#sensor = ms5837.MS5837(model=ms5837.MS5837_MODEL_30BA, bus=0) 
sensor = ms5837.MS5837_30BA()  # Change to MS5837_02BA if using Bar02


if not sensor.init():
    print("Sensor could not be initialized")
    exit(1)

try :
    while True:
        if sensor.read():
            print(("P: %0.1f mbar  %0.3f psi\tT: %0.2f C  %0.2f F") % (
                sensor.pressure(),
                sensor.pressure(ms5837.UNITS_psi),
                sensor.temperature(),
                sensor.temperature(ms5837.UNITS_Farenheit)))
            
            
            freshwaterDepth = sensor.depth() # default is freshwater
            sensor.setFluidDensity(ms5837.DENSITY_SALTWATER)
            saltwaterDepth = sensor.depth() # No nead to read() again
            sensor.setFluidDensity(1000) 
            print(("Depth: %.3f m (freshwater)  %.3f m (saltwater)") % (freshwaterDepth, saltwaterDepth))
            time.sleep(1)
        else:
            print("Sensor read failed!")
            exit(1)
            
except KeyboardInterrupt:
    print("\nShutting down sensor test.")
    

