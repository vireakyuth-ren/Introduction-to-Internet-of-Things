from machine import SoftI2C
from machine_i2c_lcd import I2cLcd

import network
import socket
import time
import dht

from machine import Pin, time_pulse_us, PWM

# DHT11 data pin
dht_sensor = dht.DHT11(Pin(33))

# HC-SR04 pins
trig = Pin(27, Pin.OUT)
echo = Pin(26, Pin.IN)

# LCD Setup
I2C_ADDR = 0x27

i2c = SoftI2C(
    sda=Pin(21),
    scl=Pin(22),
    freq=400000
)

lcd = I2cLcd(
    i2c,
    I2C_ADDR,
    2,
    16
)

lcd.clear()


### Display the text -> IoT Class on the first row
lcd.clear()
lcd.move_to(0, 0)
lcd.putstr("IoT Class")

### Display the text -> Lab 2 & Task 2 on the second Row
lcd.move_to(0, 1)
lcd.putstr("Lab 2 & Task 2")

time.sleep(2)

lcd.clear()

show_distance = False
show_temperature = False

## WIFI Setup

ssid = "BR"
password = "23456789"

## SERVO SETUP

servo = PWM(Pin(13), freq=50)
servo_angle = 90



def read_distance():
    try:
        # set Trigger to off for 2us
        trig.value(0)
        time.sleep_us(2)

        # set Trigger to on for 10us
        trig.value(1)
        time.sleep_us(10)

        # set Trigger to off again
        trig.value(0)

        # Measure the ECHO pulse
        duration = time_pulse_us(echo, 1, 30000)

        # make a codition if the duration less than 0 return None
        if duration < 0:
            return None

        # Convert time to distance in centimetres with the formular d = v*t/2
        distance = (duration * 0.0343) / 2
        return distance

    except Exception as error:
        print("Ultrasonic error:", error)
        return None

def read_dht11():
    try:
        # Call the object from the dht library
        dht_sensor.measure()

        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()

        return temperature, humidity

    except Exception as error:
        print("DHT11 error:", error)
        return None, None


def create_webpage(
    temperature,
    humidity,
    distance,
    show_distance,
    show_temperature,
    servo_angle
):

    if temperature is None:
        temperature_text = "Sensor error"
    else:
        temperature_text = (
            str(temperature) + " &deg;C"
        )

    if humidity is None:
        humidity_text = "Sensor error"
    else:
        humidity_text = (
            str(humidity) + " %"
        )

    if distance is None:
        distance_text = "Out of range"
    else:
        distance_text = (
            "{:.1f} cm".format(distance)
        )

    # TASK 2 ADDITION
    if show_distance:
        distance_button_text = "Hide Distance"
        distance_button_class = "hide-button"
    else:
        distance_button_text = "Show Distance"
        distance_button_class = "show-button"

    # TASK 2 ADDITION
    if show_temperature:
        temperature_button_text = (
            "Hide Temperature"
        )

        temperature_button_class = (
            "hide-button"
        )

    else:
        temperature_button_text = (
            "Show Temperature"
        )

        temperature_button_class = (
            "show-button"
        )

    html = """
<!DOCTYPE html>
<html>

<head>
    <title>ESP32 Sensor Monitoring</title>

    <meta name="viewport"
          content="width=device-width,
                   initial-scale=1">

    <meta http-equiv="refresh"
          content="2; URL=/">

    <style>
        body {
            font-family: Arial;
            text-align: center;
            background-color: #f2f2f2;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }

        h1 {
            color: black
        }

        .card {
            background-color: white;
            width: 30vw;
            margin: 2rem 2rem;
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);

        }

        .value {
            color: blue;
            font-size: 1.5rem;
            font-weight: bold;
        }

        button {
            border: none;
            color: white;
            padding: 1rem;
            margin: 2rem;
            border-radius: 10px;
            font-size: 1.2rem;
            cursor: pointer;
        }

        .show-button {
            background-color: blue;
        }

        .hide-button {
            background-color: black;
        }
    </style>
</head>

<body>

    <h1>ESP 32 Sensor Monitoring</h1>

    <div class="card">
        <h2>DHT11 Sensor</h2>

        <p>Temperature</p>
        <div class="value">
            TEMPERATURE_VALUE
        </div>
        <p>Humidity</p>
        <div class="value">
            HUMIDITY_VALUE
        </div>
    </div>

    <div class="card">
        <h2>HC-SR04 Sensor</h2>

        <p>Distance</p>
        <div class="value">
            DISTANCE_VALUE
        </div>
    </div>


    <!-- TASK 2 ADDITION -->

    <div class="card">
        <h2>LCD Control</h2>

        <a href="/?distance=toggle">
            <button class="DISTANCE_BUTTON_CLASS">DISTANCE_BUTTON_TEXT</button>
        </a>

        <a href="/?temperature=toggle">
            <button class="TEMPERATURE_BUTTON_CLASS">TEMPERATURE_BUTTON_TEXT</button>
        </a>

    </div>
    
        <h1>ESP32 Servo Control</h1>
 
     ## TASK 3
 
    <div class="card">
 
        <h2>Servo Angle</h2>
 
        <p class = "angle">SERVO_ANGLE</p>
 
        <input
            type="range"
            min="0"
            max="180"
            value="SERVO_ANGLE"
 
            oninput="
                document.getElementById(
                    'angle-value'
                ).innerHTML = this.value
            "
 
            onchange="
                fetch('/servo?angle=' + this.value)
            "
        >
 
        <p>Move the slider to control the servo.</p>
 
    </div>

</body>

</html>
"""

    html = html.replace(
        "TEMPERATURE_VALUE",
        temperature_text
    )

    html = html.replace(
        "HUMIDITY_VALUE",
        humidity_text
    )

    html = html.replace(
        "DISTANCE_VALUE",
        distance_text
    )



    # TASK 2 ADDITION ON WEBPAGE
    
    
    
    html = html.replace(
        "DISTANCE_BUTTON_TEXT",
        distance_button_text
    )

    html = html.replace(
        "TEMPERATURE_BUTTON_TEXT",
        temperature_button_text
    )

    html = html.replace(
        "DISTANCE_BUTTON_CLASS",
        distance_button_class
    )

    html = html.replace(
        "TEMPERATURE_BUTTON_CLASS",
        temperature_button_class
    )


    ## TASK 3
    # FIX: was `str(angle)` -- `angle` doesn't exist in this function,
    # only the `servo_angle` parameter does. That NameError was firing
    # on every request, so the page never rendered.
    html = html.replace(
        "SERVO_ANGLE",
        str(servo_angle)
    )

    return html



def clear_lcd_row(row):

    lcd.move_to(0, row)

    # 16 spaces clear the entire row
    lcd.putstr("                ")

def display_distance(distance):
    if distance is not None:
        print("Distance: {:.2f} cm".format(distance))
        lcd.move_to(0, 0)         # first row
        lcd.putstr("Dist: " + "{:.2f}".format(distance) + " cm")
    else:
        print("Distance ERROR")
        lcd.putstr("Distance ERROR")

    time.sleep(1)

def display_temperature(temperature):
    if temperature is not None:
        print("Temperature: {:.2f} cm".format(temperature))
        lcd.move_to(0, 1)         # second row
        lcd.putstr("Temp: " + str(temperature) + " C")
    else:
        print(" Temp ERROR")
        lcd.putstr("Temp ERROR")

    time.sleep(1)
    


## TASK 3: SERVO

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


wifi = network.WLAN(network.STA_IF)
wifi.active(True)

if not wifi.isconnected():
    print("Connecting to Wi-Fi...")
    wifi.connect(ssid, password)

    while not wifi.isconnected():
        print(".", end="")
        time.sleep(1)

ip = wifi.ifconfig()[0]

print()
print("Wi-Fi connected!")
print("ESP32 IP address:", ip)
print("Open this address in your browser:")
print("http://" + ip)


# ==============================
# START WEB SERVER
# ==============================

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

print("Web server is running...")

while True:

    client = None
    
    try:
        client, client_address = server.accept()

        print("Browser connected:", client_address)

        # Receive browser request and decode to a string so the
        # "in" checks below work (recv() returns raw bytes).
        request = client.recv(1024).decode()
        print("Request received")
        
        request_line = request.split(
            "\r\n")[0]

        # Read sensors
        temperature, humidity = read_dht11()
        distance = read_distance()

        print("Temperature:", temperature)
        print("Humidity:", humidity)
        print("Distance:", distance)


        # TASK 2: DISTANCE BUTTON

        if "/?distance=toggle" in request:

            show_distance = not show_distance

            if show_distance:
                display_distance(distance)
                print("Distance shown on LCD")
            else:
                clear_lcd_row(0)
                print("Distance hidden")

        # TASK 2: TEMPERATURE BUTTON

        elif "/?temperature=toggle" in request:

            show_temperature = not show_temperature

            if show_temperature:
                display_temperature(temperature)
                print("Temperature shown on LCD")
            else:
                clear_lcd_row(1)
                print("Temperature hidden")

        # Keep whichever rows are toggled on updated with fresh readings
        if show_distance:
            display_distance(distance)

        if show_temperature:
            display_temperature(temperature)
            
            
            
        # TASK 3 RECEIVE SLIDER ANGLE
 
        # INITIAL SERVO POSITION
        move_servo(servo_angle)
 
        if "GET /servo?angle=" in request_line:
 
            try:
                start = request_line.find("angle=") + len("angle=")
                end = request_line.find(" ", start)
                angle_text = request_line[start:end]
                servo_angle = int(angle_text)
                move_servo(servo_angle)
 
                client.send(
                    "HTTP/1.1 204 No Content\r\n"
                )
 
                client.send(
                    "Connection: close\r\n"
                )
 
                client.send("\r\n")
 
            except Exception as error:
                print(
                    "Servo control error:",
                    error
                )

            # FIX: without this, execution fell through to the code
            # below, which builds the full HTML page and sends a
            # SECOND "HTTP/1.1 200 OK" response on the same socket
            # that we already told to close (Connection: close) in
            # the 204 response above. The browser tears the socket
            # down after the 204, so the second send() fails with a
            # connection reset -- which is what looks like the page
            # "losing connection" right after moving the slider.
            # The finally block below still runs and closes the
            # socket, so this is safe.
            continue

        # Create webpage
        webpage = create_webpage(
            temperature,
            humidity,
            distance,
            show_distance,
            show_temperature,
            servo_angle
        )

        # Send HTTP response
        client.send("HTTP/1.1 200 OK\r\n")
        client.send("Content-Type: text/html\r\n")
        client.send("Connection: close\r\n")
        client.send("\r\n")
        client.sendall(webpage)

    except Exception as error:
        print("Server error:", error)

        # Without this, a failure above (e.g. an I2C error from the
        # LCD) leaves the browser with zero bytes -> ERR_EMPTY_RESPONSE.
        # Send back something so the failure is visible in the browser
        # too, not just the serial console.
        if client is not None:
            try:
                error_body = "Server error: " + str(error)
                client.send("HTTP/1.1 500 Internal Server Error\r\n")
                client.send("Content-Type: text/plain\r\n")
                client.send("Connection: close\r\n")
                client.send("\r\n")
                client.sendall(error_body)
            except Exception as send_error:
                print("Failed to send error response:", send_error)

    finally:
        if client is not None:
            client.close()