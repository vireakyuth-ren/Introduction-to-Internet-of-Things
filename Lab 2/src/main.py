import network
import socket
import time
import dht
import json
from machine import Pin, SoftI2C, time_pulse_us, PWM
from machine_i2c_lcd import I2cLcd

dht_sensor = dht.DHT11(Pin(33))

trig = Pin(27, Pin.OUT)
echo = Pin(26, Pin.IN)

I2C_ADDR = 0x27
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)

lcd.clear()
lcd.move_to(0, 0)
lcd.putstr("IoT Class")
lcd.move_to(0, 1)
lcd.putstr("Lab 2 & main.py")
time.sleep(2)
lcd.clear()

show_distance = False
show_temperature = False

ssid = "BR"
password = "23456789"

# Servo setup (signal wire on GPIO 13)
servo = PWM(Pin(13), freq=50)
servo_angle = 90


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


def url_decode(text):
    result = ""
    i = 0

    while i < len(text):

        if text[i] == "%":
            try:
                hex_value = text[i + 1:i + 3]
                result += chr(int(hex_value, 16))
                i += 3
            except:
                result += text[i]
                i += 1

        elif text[i] == "+":
            result += " "
            i += 1

        else:
            result += text[i]
            i += 1

    return result


def display_message(message):
    lcd.clear()

    if len(message) <= 16:
        lcd.move_to(0, 0)
        lcd.putstr(message)

    else:
        message = "                " + message + "                "

        for i in range(len(message) - 15):
            lcd.move_to(0, 0)
            lcd.putstr(message[i:i + 16])
            time.sleep_ms(300)


def format_readings(temperature, humidity, distance):
    temperature_text = (
        "Sensor error"
        if temperature is None
        else f"{temperature} &deg;C"
    )

    humidity_text = (
        "Sensor error"
        if humidity is None
        else f"{humidity} %"
    )

    distance_text = (
        "Out of range"
        if distance is None
        else f"{distance:.1f} cm"
    )

    return temperature_text, humidity_text, distance_text


def create_webpage(
    temperature,
    humidity,
    distance,
    show_distance,
    show_temperature,
    servo_angle
):
    temperature_text, humidity_text, distance_text = format_readings(
        temperature,
        humidity,
        distance
    )

    distance_btn_text = (
        "Hide Distance"
        if show_distance
        else "Show Distance"
    )

    distance_btn_class = (
        "hide-button"
        if show_distance
        else "show-button"
    )

    temp_btn_text = (
        "Hide Temperature"
        if show_temperature
        else "Show Temperature"
    )

    temp_btn_class = (
        "hide-button"
        if show_temperature
        else "show-button"
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ESP32 Sensor Monitoring</title>

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

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

        .show-button {{
            background-color: #007bff;
        }}

        .hide-button {{
            background-color: #333333;
        }}

        input {{
            width: 80%;
            padding: 0.8rem;
            border: 1px solid #ccc;
            border-radius: 8px;
            font-size: 1rem;
            box-sizing: border-box;
        }}
    </style>
</head>

<body>

    <h1>ESP32 Sensor Monitoring</h1>

    <div class="card">
        <h2>DHT11 Sensor</h2>

        <p>Temperature</p>
        <div class="value" id="temperature">{temperature_text}</div>

        <p>Humidity</p>
        <div class="value" id="humidity">{humidity_text}</div>
    </div>

    <div class="card">
        <h2>HC-SR04 Sensor</h2>

        <p>Distance</p>
        <div class="value" id="distance">{distance_text}</div>
    </div>

    <div class="card">
        <h2>LCD Control</h2>

        <a href="/?distance=toggle">
            <button class="{distance_btn_class}">
                {distance_btn_text}
            </button>
        </a>

        <a href="/?temperature=toggle">
            <button class="{temp_btn_class}">
                {temp_btn_text}
            </button>
        </a>
    </div>

    <div class="card">
        <h2>Send Text to LCD</h2>

        <input
            type="text"
            id="message"
            placeholder="Type message..."
            maxlength="100"
        >

        <br>

        <button onclick="sendMessage()">
            Send
        </button>

        <p id="status"></p>
    </div>

    <div class="card">
        <h2>Servo Control</h2>

        <p>Angle</p>
        <div class="value"><span id="angle-value">{servo_angle}</span>&deg;</div>

        <input
            type="range"
            min="0"
            max="180"
            value="{servo_angle}"
            oninput="document.getElementById('angle-value').innerHTML = this.value"
            onchange="fetch('/servo?angle=' + this.value)"
        >

        <p>Move the slider to control the servo.</p>
    </div>

    <script>
        function updateSensors() {{

            fetch("/data")
            .then(function(response) {{
                return response.json();
            }})
            .then(function(data) {{

                document.getElementById("temperature").innerHTML =
                    data.temperature;

                document.getElementById("humidity").innerHTML =
                    data.humidity;

                document.getElementById("distance").innerHTML =
                    data.distance;

            }})
            .catch(function() {{}});
        }}

        setInterval(updateSensors, 2000);

        function sendMessage() {{

            const message =
                document.getElementById("message").value;

            if (message.trim() === "") {{

                document.getElementById("status").innerHTML =
                    "Please enter some text.";

                return;
            }}

            fetch(
                "/message?text=" +
                encodeURIComponent(message)
            )
            .then(function() {{

                document.getElementById("status").innerHTML =
                    "Message sent to LCD!";

            }})
            .catch(function() {{

                document.getElementById("status").innerHTML =
                    "Failed to send message.";

            }});
        }}
    </script>

</body>
</html>"""

    return html


def clear_lcd_row(row):
    lcd.move_to(0, row)
    lcd.putstr("                ")


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


def move_servo(angle):

    # Keep the angle between 0 and 180 degrees
    if angle < 0:
        angle = 0

    if angle > 180:
        angle = 180

    min_duty = 26
    max_duty = 128

    # Convert angle 0-180 degrees to a duty value in [min_duty, max_duty]
    duty = int(
        min_duty
        + (angle / 180)
        * (max_duty - min_duty)
    )

    # Send the calculated duty to the servo
    servo.duty(duty)

    print("Servo angle:", angle)
    print("PWM duty:", duty)


# Initial servo position
move_servo(servo_angle)


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

    print(
        f"\nWi-Fi connected! IP address: http://{ip}"
    )

else:

    print("\nWi-Fi connection failed!")


address = socket.getaddrinfo(
    "0.0.0.0",
    80
)[0][-1]

server = socket.socket()

server.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)

server.bind(address)
server.listen(1)

server.settimeout(0.2)

print("Web server is running...")


while True:

    client = None

    try:

        client, client_address = server.accept()

        print(
            "Browser connected:",
            client_address
        )

        request = client.recv(1024).decode()

        print("Request received")

        request_line = request.split("\r\n")[0]


        if "GET /message?text=" in request_line:

            start = (
                request_line.find("text=")
                + len("text=")
            )

            end = request_line.find(
                " ",
                start
            )

            encoded_message = request_line[
                start:end
            ]

            message = url_decode(
                encoded_message
            )

            print(
                "Message:",
                message
            )

            client.send(
                "HTTP/1.1 204 No Content\r\n"
            )

            client.send(
                "Connection: close\r\n"
            )

            client.send("\r\n")

            client.close()
            client = None

            display_message(message)

            continue


        if "GET /servo?angle=" in request_line:

            try:
                start = (
                    request_line.find("angle=")
                    + len("angle=")
                )

                end = request_line.find(
                    " ",
                    start
                )

                servo_angle = int(
                    request_line[start:end]
                )

                if servo_angle < 0:
                    servo_angle = 0

                if servo_angle > 180:
                    servo_angle = 180

                move_servo(servo_angle)

            except Exception as error:
                print(
                    "Servo control error:",
                    error
                )

            client.send(
                "HTTP/1.1 204 No Content\r\n"
            )

            client.send(
                "Connection: close\r\n"
            )

            client.send("\r\n")

            continue


        if "GET /data" in request_line:

            temperature, humidity = read_dht11()

            distance = read_distance()

            if show_distance:
                display_distance(distance)

            if show_temperature:
                display_temperature(temperature)

            temperature_text, humidity_text, distance_text = (
                format_readings(
                    temperature,
                    humidity,
                    distance
                )
            )

            body = json.dumps({
                "temperature": temperature_text,
                "humidity": humidity_text,
                "distance": distance_text
            })

            client.send(
                "HTTP/1.1 200 OK\r\n"
            )

            client.send(
                "Content-Type: application/json\r\n"
            )

            client.send(
                "Connection: close\r\n"
            )

            client.send("\r\n")

            client.sendall(
                body.encode("utf-8")
            )

            continue


        temperature, humidity = read_dht11()

        distance = read_distance()

        print(
            "Temperature:",
            temperature
        )

        print(
            "Humidity:",
            humidity
        )

        print(
            "Distance:",
            distance
        )


        if "/?distance=toggle" in request_line:

            show_distance = not show_distance

            if show_distance:

                display_distance(distance)

                print(
                    "Distance shown on LCD"
                )

            else:

                clear_lcd_row(0)

                print(
                    "Distance hidden"
                )


        elif "/?temperature=toggle" in request_line:

            show_temperature = not show_temperature

            if show_temperature:

                display_temperature(
                    temperature
                )

                print(
                    "Temperature shown on LCD"
                )

            else:

                clear_lcd_row(1)

                print(
                    "Temperature hidden"
                )


        if show_distance:
            display_distance(distance)

        if show_temperature:
            display_temperature(
                temperature
            )


        webpage = create_webpage(
            temperature,
            humidity,
            distance,
            show_distance,
            show_temperature,
            servo_angle
        )


        client.send(
            "HTTP/1.1 200 OK\r\n"
        )

        client.send(
            "Content-Type: text/html\r\n"
        )

        client.send(
            "Connection: close\r\n"
        )

        client.send("\r\n")

        client.sendall(
            webpage.encode("utf-8")
        )


    except Exception as error:

        print(
            "Server error:",
            error
        )

        if client is not None:

            try:

                error_body = (
                    "Server error: "
                    + str(error)
                )

                client.send(
                    "HTTP/1.1 500 Internal Server Error\r\n"
                )

                client.send(
                    "Content-Type: text/plain\r\n"
                )

                client.send(
                    "Connection: close\r\n"
                )

                client.send("\r\n")

                client.sendall(
                    error_body.encode("utf-8")
                )

            except Exception as send_error:

                print(
                    "Failed to send error response:",
                    send_error
                )


    finally:

        if client is not None:
            client.close()
