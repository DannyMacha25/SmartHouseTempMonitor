import machine, onewire, ds18x20, time
import network
import socket
from time import sleep
from secrets import Secret

def ConnectToWifi():
    #Connect to WLAN
    print('[Network] Beginning connection to wifi...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(Secret.ssid, Secret.password)
    while wlan.isconnected() == False:
        print('[Network] Waiting for connection...')
        sleep(1)
    return wlan
def ConnectToServer(wlan):
    own_ip = wlan.ifconfig()[0]
    print('[Prog] Connected to Wifi.')
    print('[Network] Connecting to server...')
    
    s = socket.socket()
    try:
        s.connect(('192.168.50.173',1024)) # NOTE: Parametrize
    except:
        print('[Network] Connection failed... Trying again...')  
    
    # Initialize connection to Server
    device_type = 'p'
    device_id = '01' # NOTE: Parametrize
    print('[Newtwork] Connected, sending initialization data...')
    sleep(1)
    try:
        message = '%s %s'%(device_type, device_id)
        s.send(message.encode())
        print('[Network] Succesfully sent device info to Server!')
    except:
        print('[Network] Failed to send message...')
    
    # Return reference to socket
    return s

def CollectTempData(roms, ds_sensor):
    try:
        ds_sensor.convert_temp()
    except:
        print('Connection Bad 1')
        time.sleep(1)
        return -200
    for rom in roms:
        tempC = 0
        try:
            tempC = ds_sensor.read_temp(rom)
        except:
            print('Connection Bad')
        tempF = tempC * (9/5) + 32
        return tempF


def main():
    # Start Client!
    print('[Prog] Program Starting')
    
    # Connect to Wifi
    wlan = None
    try:
        wlan = ConnectToWifi()
    except KeyboardInterrupt:
        machine.reset()
    
    # Initialize Temperature Hardware
    ds_pin = machine.Pin(21) # NOTE: Parametrize
    ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
    roms = ds_sensor.scan()
    
    while roms == None:
        print('[Error] No sensors found')
        roms = ds_sensor.scan()
    print('[Prog] Found sensor')

    # Collect one for fun
    temp = CollectTempData(roms, ds_sensor)
    print('[Debug] Temp: %f'%(temp))
    sleep(1)

    # Connect to Server
    s = ConnectToServer(wlan)
    
    # Send temperature data
    while True:
        temp = CollectTempData(roms, ds_sensor)
        sleep(2)
        try:
            s.send(('t ' + str(temp)).encode()) # Send temperature in F
        except:
            print('[Network] Lost connection, retrying...')
            s = ConnectToServer(wlan)
        
    s.close()
        
if __name__ == '__main__':
    main()
