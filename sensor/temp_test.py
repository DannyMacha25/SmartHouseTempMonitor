import machine, onewire, ds18x20, time

ds_pin = machine.Pin(21)
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))

roms = ds_sensor.scan()
print('Found DS devices: ', roms)

while True:
    try:
        ds_sensor.convert_temp()
    except:
        print('Connection Bad 1')
        time.sleep(1)
        continue
    time.sleep_ms(75)
    for rom in roms:
        print(rom)
        tempC = 0
        try:
            tempC = ds_sensor.read_temp(rom)
        except:
            print('Connection Bad')
        tempF = tempC * (9/5) + 32
        print('Temperate (F): %.2f'%(tempF))
        time.sleep(5)