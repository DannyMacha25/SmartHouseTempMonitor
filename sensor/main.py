import machine, onewire, ds18x20, time
import network
import socket

from time import sleep
from secrets import Secret
from umqtt.simple import MQTTClient
import json

MQTT = 0
SERVER = 1

# CONFIG
CONNECTION_TYPE = MQTT
DEVICE_ID = '01'

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
    print('[Newtwork] Connected, sending initialization data...')
    sleep(1)
    try:
        message = '%s %s'%(device_type, DEVICE_ID)
        s.send(message.encode())
        print('[Network] Succesfully sent device info to Server!')
    except:
        print('[Network] Failed to send message...')
    
    # Return reference to socket
    return s

def ConfigureMQTT():
    mqtt_host = '192.168.50.134' # Parameterize
    mqtt_username = Secret.mqtt_username
    mqtt_password = Secret.mqtt_password
    mqtt_client_id = DEVICE_ID
    
    mqtt_client = MQTTClient(
        client_id=mqtt_client_id,
        server=mqtt_host,
        user=mqtt_username,
        password=mqtt_password)
    
    return mqtt_client

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
    
def DiscoveryMQTT(client):
    output_json = {
    "name" : "null",
    "state_topic" : "sensor/temperature/" + DEVICE_ID,
    "unique_id" : "temp01",
    "unit_of_measurement" : "°F",
    "device": {"name" : "Temp Sensor", "identifiers" : ["temp01"]}
    }
    mqtt_discovery_topic = 'homeassistant/sensor/temp' + DEVICE_ID +'/config'
    
    json_obj = json.dumps(output_json)
    
    client.publish(mqtt_discovery_topic, json_obj)


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

    # Connect to Server/MQTT
    if CONNECTION_TYPE == SERVER:
        s = ConnectToServer(wlan)
    elif CONNECTION_TYPE == MQTT:
        mqtt_client = ConfigureMQTT()
        mqtt_publish_topic = 'sensor/temperature/' + DEVICE_ID
        mqtt_client.connect()
        #DiscoveryMQTT(mqtt_client) dont work
        
        
    # Send temperature data
    while True:
        temp = CollectTempData(roms, ds_sensor)
        sleep(2)
        if CONNECTION_TYPE == SERVER:
            try:
                s.send(('t ' + str(temp)).encode()) # Send temperature in F
            except:
                print('[Network] Lost connection, retrying...')
                s = ConnectToServer(wlan)
        elif CONNECTION_TYPE == MQTT:
            try:
                mqtt_client.publish(mqtt_publish_topic,str(temp))
            except:
                print('Could not publish, aw well')
        
    s.close()
        
if __name__ == '__main__':
    main()
