import machine, onewire, ds18x20, time
import network
import socket

from time import sleep
from secrets import Secret
from umqtt.simple import MQTTClient
import json
MQTT = 0
SERVER = 1

# Read config file
with open('config.json', 'r') as file:
    config = json.load(file)

# CONFIG
CONNECTION_TYPE = MQTT # Hardset
DEVICE_ID = config['device_id']
IP = config['ip']

def ConnectToWifi():
    """
    Connects the raspberry pi to the network
    """
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
    """
    Connects the raspberry pi to the custom server, if in server mode
    """
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
    """
    Configures an MQTT client object
    
    Returns
        mqtt_cleint : MQTTClient object
    """
    mqtt_host = IP # Parameterize
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
    """
    Collects data from the connected temperature sensor
    
    Returns
        tempF: Float
    """
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
    """
    Creates and publishes a discovery request, made for HomeAssistant
    NOTE: Never got this to work :(
    """
    output_json = {
    "name" : "null",
    "state_topic" : "sensor/temperature/" + DEVICE_ID,
    "unique_id" : "temp" + DEVICE_ID,
    "unit_of_measurement" : "°F",
    "device": {"name" : "Temp Sensor", "identifiers" : ["temp01"]}
    }
    mqtt_discovery_topic = 'homeassistant/sensor/temp' + DEVICE_ID +'/config'
    
    json_obj = json.dumps(output_json)
    
    client.publish(mqtt_discovery_topic, json_obj)


def main():
    """
    Where all of the magic happens!
    """
    
    # Start Client!
    print('[Prog] Program Starting')
    
    # Connect to Wifi
    wlan = None
    try:
        wlan = ConnectToWifi()
    except KeyboardInterrupt:
        machine.reset()
    
    # Initialize Sensor Hardware
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
    server = None
    if CONNECTION_TYPE == SERVER:
        server = ConnectToServer(wlan)
    elif CONNECTION_TYPE == MQTT:
        mqtt_client = ConfigureMQTT()
        mqtt_publish_topic = 'sensor/temperature/' + DEVICE_ID
        mqtt_client.connect()
        

    #NOTE: Maybe add median stuff later
    # Send temperature data
    while True:
        temp = CollectTempData(roms, ds_sensor) # Collect temp
        sleep(2)
        
        if CONNECTION_TYPE == SERVER:
            try:
                output = np.median(temperature_array)
                server.send(('t ' + str(temp)).encode()) # Send temperature in F
            except:
                print('[Network] Lost connection, retrying...')
                server = ConnectToServer(wlan)
        elif CONNECTION_TYPE == MQTT:
            try:
                mqtt_client.publish(mqtt_publish_topic,str(temp))
            except:
                print('Could not publish, aw well')
    
    # Close connections
    if server != None:
        s.close()
        
if __name__ == '__main__':
    main()
