import network
import socket
import time
import dht
from machine import Pin, SoftI2C, time_pulse_us
from machine_i2c_lcd import I2cLcd

# DHT11 Data Pin
dht_sensor = dht.DHT11(Pin(33))

# HC-SR04 Pins
trig = Pin(27, Pin.OUT)
echo = Pin(26, Pin.IN)

# LCD Setup
I2C_ADDR = 0x27
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)

# Initial LCD Display
lcd.clear()
lcd.move_to(0, 0)
lcd.putstr("IoT Class")
lcd.move_to(0, 1)
lcd.putstr("Lab 2 & Task 2")
time.sleep(2)
lcd.clear()

# Display toggle state tracking
show_distance = False
show_temperature = False

# Wi-Fi Configuration
ssid = "BR"
password = "23456789"


def read_distance():
    try:
        trig.value(0)
        time.sleep_us(2)
        trig.value(1)
        time.sleep_us(10)
        trig.value(0)

        duration = time_pulse_us(echo, 1, 30000)
        if duration < 0:
            return None

        return (duration * 0.0343) / 2
    except Exception as error:
        print("Ultrasonic error:", error)
        return None


def read_dht11():
    try:
        dht_sensor.measure()
        return dht_sensor.temperature(), dht_sensor.humidity()
    except Exception as error:
        print("DHT11 error:", error)
        return None, None


def create_webpage(temperature, humidity, distance, show_distance, show_temperature):
    temperature_text = "Sensor error" if temperature is None else f"{temperature} &deg;C"
    humidity_text = "Sensor error" if humidity is None else f"{humidity} %"
    distance_text = "Out of range" if distance is None else f"{distance:.1f} cm"

    distance_btn_text = "Hide Distance" if show_distance else "Show Distance"
    distance_btn_class = "hide-button" if show_distance else "show-button"

    temp_btn_text = "Hide Temperature" if show_temperature else "Show Temperature"
    temp_btn_class = "hide-button" if show_temperature else "show-button"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Sensor Monitoring</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            font-family: Arial, sans-serif;
            text-align: center;
            background-color: #f2f2f2;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        h1 {{ color: #333; }}
        .card {{
            background-color: white;
            width: 90%;
            max-width: 360px;
            margin: 1rem 0;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }}
        .value {{
            color: #007bff;
            font-size: 1.5rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }}
        button {{
            border: none;
            color: white;
            padding: 0.8rem 1.2rem;
            margin: 0.5rem;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            width: 80%;
        }}
        .show-button {{ background-color: #007bff; }}
        .hide-button {{ background-color: #333333; }}
    </style>
</head>
<body>
    <h1>ESP32 Sensor Monitoring</h1>

    <div class="card">
        <h2>DHT11 Sensor</h2>
        <p>Temperature</p>
        <div class="value">{temperature_text}</div>
        <p>Humidity</p>
        <div class="value">{humidity_text}</div>
    </div>

    <div class="card">
        <h2>HC-SR04 Sensor</h2>
        <p>Distance</p>
        <div class="value">{distance_text}</div>
    </div>

    <div class="card">
        <h2>LCD Control</h2>
        <a href="/?distance=toggle">
            <button class="{distance_btn_class}">{distance_btn_text}</button>
        </a>
        <a href="/?temperature=toggle">
            <button class="{temp_btn_class}">{temp_btn_text}</button>
        </a>
    </div>
</body>
</html>"""
    return html


def clear_lcd_row(row):
    lcd.move_to(0, row)
    lcd.putstr("                ")  # 16 blank spaces


def display_distance(distance):
    lcd.move_to(0, 0)
    if distance is not None:
        lcd.putstr(f"Dist: {distance:.1f} cm   ")
    else:
        lcd.putstr("Dist: ERROR     ")


def display_temperature(temperature):
    lcd.move_to(0, 1)
    if temperature is None:
        lcd.putstr("Temp: ERROR     ")
    else:
        lcd.putstr(f"Temp: {temperature} C     ")


# Safe Wi-Fi Initialization
wifi = network.WLAN(network.STA_IF)
if wifi.active():
    wifi.active(False)
    time.sleep(0.5)
wifi.active(True)

if not wifi.isconnected():
    print("Connecting to Wi-Fi...")
    wifi.connect(ssid, password)
    timeout = 10
    while not wifi.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1

if wifi.isconnected():
    ip = wifi.ifconfig()[0]
    print(f"\nWi-Fi connected! IP address: http://{ip}")
else:
    print("\nWi-Fi connection failed!")

# Start Web Server
address = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(address)
server.listen(1)
server.settimeout(0.2)  # Non-blocking timeout so LCD updates independently

print("Web server is running...")

while True:
    client = None
    try:
        # 1. Read Sensors
        temperature, humidity = read_dht11()
        distance = read_distance()

        # 2. Check for incoming HTTP Requests
        try:
            client, client_address = server.accept()
            request = client.recv(1024).decode()

            if "/?distance=toggle" in request:
                show_distance = not show_distance
                if not show_distance:
                    clear_lcd_row(0)

            elif "/?temperature=toggle" in request:
                show_temperature = not show_temperature
                if not show_temperature:
                    clear_lcd_row(1)

            # Build & Send Web Page response
            webpage = create_webpage(
                temperature, humidity, distance, show_distance, show_temperature
            )
            client.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
            client.sendall(webpage.encode("utf-8"))

        except OSError:
            # Socket timeout (no client connected in this loop iteration)
            pass

        # 3. Update LCD dynamically regardless of HTTP requests
        if show_distance:
            display_distance(distance)

        if show_temperature:
            display_temperature(temperature)

    except Exception as error:
        print("Server error:", error)

    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

    time.sleep(0.5)  # Loop interval