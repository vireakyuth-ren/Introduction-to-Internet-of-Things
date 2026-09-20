import network
import socket
import time
import dht
from machine import Pin, time_pulse_us

# DHT11 data pin
dht_sensor = dht.DHT11(Pin(33))

# HC-SR04 pins
trig = Pin(27, Pin.OUT)
echo = Pin(26, Pin.IN)

# Wi-Fi Setup
ssid = "BR"
password = "23456789"


def read_distance():
    try:
        # Trigger pulse (10us)
        trig.value(0)
        time.sleep_us(2)
        trig.value(1)
        time.sleep_us(10)
        trig.value(0)

        # Measure ECHO pulse (timeout after 30ms / ~5 meters)
        duration = time_pulse_us(echo, 1, 30000)

        if duration < 0:
            return None

        # Distance = (duration * speed_of_sound_cm_per_us) / 2
        distance = (duration * 0.0343) / 2
        return distance

    except Exception as error:
        print("Ultrasonic error:", error)
        return None


def read_dht11():
    try:
        dht_sensor.measure()
        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        return temperature, humidity
    except Exception as error:
        print("DHT11 error:", error)
        return None, None


def create_webpage(temperature, humidity, distance):
    temperature_text = "Sensor error" if temperature is None else f"{temperature} &deg;C"
    humidity_text = "Sensor error" if humidity is None else f"{humidity} %"
    distance_text = "Out of range" if distance is None else f"{distance:.1f} cm"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Sensor Monitoring</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="3">
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
        h1 {{
            color: #333;
        }}
        .card {{
            background-color: white;
            width: 90%;
            max-width: 350px;
            margin: 1rem 0;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        }}
        .value {{
            color: #007bff;
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }}
    </style>
</head>
<body>
    <h1>ESP32 Sensor Dashboard</h1>

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
</body>
</html>"""

    return html


# Connect to Wi-Fi
wifi = network.WLAN(network.STA_IF)
if wifi.active():
    wifi.active(False)
    time.sleep(0.5)
wifi.active(True)

if not wifi.isconnected():
    print("Connecting...")
    wifi.connect(ssid, password)
    for _ in range(10):
        if wifi.isconnected():
            break
        print(".", end="")
        time.sleep(1)

ip = wifi.ifconfig()[0]
print("\nWi-Fi connected!")
print("ESP32 IP address:", ip)
print(f"Open in web browser: http://{ip}\n")

# Start Web Server
address = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(address)
server.listen(1)

print("Web server running...")

while True:
    client = None
    try:
        client, client_address = server.accept()
        print("Browser connected:", client_address)

        # Receive request
        request = client.recv(1024)

        # Read sensors
        temperature, humidity = read_dht11()
        distance = read_distance()

        # Send HTTP Response
        webpage = create_webpage(temperature, humidity, distance)
        client.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
        client.sendall(webpage.encode('utf-8'))

    except Exception as error:
        print("Server error:", error)

    finally:
        if client is not None:
            client.close()