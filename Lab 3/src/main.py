from machine import Pin, PWM
from tm1637 import TM1637
import network
import time
import urequests as requests


# ---------- CONFIG ----------
WIFI_SSID = ""
WIFI_PASS = ""

BLYNK_TOKEN = ""
BLYNK_API   = "http://blynk.cloud/external/api"

CLOSED_ANGLE = 45
OPEN_ANGLE   = 115
POLL      = 700      # how often to poll Blynk for mode / slider (in miliseconds)
CLOSE_DELAY = 2000    # sensor must stay clear this long before gate closes

# -------------- PIN --------------
ir = Pin(4, Pin.IN)
servo = PWM(Pin(13), freq=50)
tm = TM1637(clk_pin=17, dio_pin=16, brightness=5)

# ---------- WIFI ----------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(WIFI_SSID, WIFI_PASS)

print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)
print("WiFi connected!")


# ----- Task 1 ------
def send_IR_status(status):
    url = f"{BLYNK_API}/update?token={BLYNK_TOKEN}&V0={status}"
    r = requests.get(url)
    r.close()


# ----- Task 2 -----
def move_servo(angle):
    # Keep the angle between 45 and 115 degrees
    if angle < 45:
        angle = 45
    if angle > 115:
        angle = 115

    min_duty = 26
    max_duty = 128

    # Convert angle 0-180 degrees to a duty value in [min_duty, max_duty]
    duty = int(min_duty + (angle / 180) * (max_duty - min_duty))

    servo.duty(duty)
    print("Servo angle:", angle, "| PWM duty:", duty)


def get_servo_angle():
    r = requests.get(f"{BLYNK_API}/get?token={BLYNK_TOKEN}&V1")
    angle = int(float(str(r.text).strip('[]"{}')))
    r.close()
    return angle

# ---------- Task 3 ----------
def register_detection():
    global count
    count += 1
    print("Detections:", count)
    tm.show_number(count)
    send_car_count(count)


# ----- Task 4 -----
def send_car_count(count):
    url = f"{BLYNK_API}/update?token={BLYNK_TOKEN}&V2={count}"
    r = requests.get(url)
    r.close()


# ----- Task 5 -----
def get_mode():
    r = requests.get(f"{BLYNK_API}/get?token={BLYNK_TOKEN}&V3")
    mode = int(float(str(r.text).strip('[]"{}')))
    r.close()
    return mode


# ---------- STATE ----------
count = 0
gate_open = False        # is the gate currently open?
clear_since = None       # when the sensor last went clear (None = object present)
last_value = None        # last IR reading (for change detection)
mode = 0
last_mode = None
last_angle = None
last_poll = time.ticks_ms()


# ---------- MODES ----------
def automatic(value):
    global gate_open, clear_since

    if value == 0:
        clear_since = None

        # New detection: open the gate once and count it once
        if not gate_open:
            print("Opening the gate..")
            move_servo(OPEN_ANGLE)
            gate_open = True
            register_detection()

    elif gate_open:
        # Sensor clear and gate open: start / check the close timer (non-blocking)
        now = time.ticks_ms()
        if clear_since is None:
            clear_since = now
            print("No Objects, closing soon..")
        elif time.ticks_diff(now, clear_since) >= CLOSE_DELAY:
            print("Closing the gate..")
            move_servo(CLOSED_ANGLE)
            gate_open = False
            clear_since = None


def manual():
    global last_angle
    # Slider is polled in the main loop; servo only moves when it changes
    angle = get_servo_angle()
    if angle != last_angle:
        move_servo(angle)
        last_angle = angle


# ---------- MAIN ----------
print("Welcome!")
tm.show_number(count)
send_car_count(count)
move_servo(CLOSED_ANGLE)

while True:
    try:
        value = ir.value()
        if value != last_value:
            if value == 0:
                print("Detected")
                send_IR_status("Detected")

                if mode == 1:
                    register_detection()
            else:
                print("Not Detected")
                send_IR_status("Not%20detected")
            last_value = value

        now = time.ticks_ms()
        if time.ticks_diff(now, last_poll) >= POLL:
            last_poll = now
            mode = get_mode()

            if mode != last_mode:
                print("Mode:", "Manual" if mode == 1 else "Automatic")
                gate_open = False
                clear_since = None
                if mode == 0:
                    move_servo(CLOSED_ANGLE)   # start Automatic with gate closed
                else:
                    last_angle = None          # force servo to follow slider
                last_mode = mode

            if mode == 1:
                manual()
 
        # ----- Automatic mode -----
        if mode == 0:
            automatic(value)

        time.sleep(0.05)

    except Exception as e:
        print("Error:", e)
        time.sleep(1)
