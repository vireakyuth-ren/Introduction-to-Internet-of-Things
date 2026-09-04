import network
import urequests
import time
from machine import Pin
import dht

# ---------- CONFIGURATION ----------
SSID = "Robotic WIFI"
PASSWORD = "rbtWIFI@2025"

BOT_TOKEN = "8829589235:AAHRBUlIfHNW1xptcZeADACtZ2vxgYRZ24o"
CHAT_ID = "-5315094504"            # <-- Default chat ID for system alerts

# Base URL for API endpoints
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---------- HARDWARE SETUP ----------
sensor = dht.DHT11(Pin(4))
relay = Pin(2, Pin.OUT)

# ---------- STATE TRACKING ----------
last_update_id = 0
relay_state = "OFF"
bot_started = False   # <-- gates monitoring/alerts until /start is received

def connect_wifi():
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    if not wifi.isconnected():
        print("Connecting to WiFi...")
        wifi.connect(SSID, PASSWORD)
        timeout = 20
        while not wifi.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
    if wifi.isconnected():
        print("WiFi connected:", wifi.ifconfig())
    else:
        print("WiFi connection failed")
    return wifi

def get_updates():
    global last_update_id
    # Fixed the incorrect URL endpoint nesting
    url = f"{BASE_URL}/getUpdates?offset={last_update_id + 1}&timeout=5"
    try:
        response = urequests.get(url)
        data = response.json()
        response.close()
        return data.get("result", [])
    except Exception as e:
        print("Error getting updates:", e)
        return []

# Updated to accept a specific chat_id dynamically, but fallback to default group
def send_message(text, target_chat_id=CHAT_ID):
    try:
        url = f"{BASE_URL}/sendMessage"
        r = urequests.post(url, json={"chat_id": target_chat_id, "text": text})
        r.close()
        print("Sent:", text)
    except Exception as e:
        print("Telegram send failed:", e)

def toggle_relay_on():
    global relay_state
    if relay_state == "ON":
        return relay_state
    relay.value(1)
    print("Relay ON")
    relay_state = "ON"
    return relay_state

def toggle_relay_off():
    global relay_state
    if relay_state == "OFF":
        return relay_state
    relay.value(0)
    print("Relay OFF")
    relay_state = "OFF"
    return relay_state

def read_dht():
    sensor.measure()
    # DHT11 only gives integers; float conversion handles the :.2f display format smoothly
    return float(sensor.temperature()), float(sensor.humidity())

def alert(temp, relay_state):
    if temp < 28 and relay_state == "OFF":
        return
    elif temp >= 28 and relay_state == "OFF":
        alert_message = f"Alert! Temperature is {temp:.2f}"
        return alert_message
    elif relay_state == "ON":
        if temp < 28:
            toggle_relay_off()
            alert_message = f"auto-OFF"
            return alert_message
        else:
            return
    else:
        return


# ---------- MAIN LOOP ----------
wifi = connect_wifi()
print("Bot booted. Waiting for /start...")
send_message("Welcome to IOT DJ BOT. Use /start to start monitoring temperature.")

while True:
    try:
        if not wifi.isconnected():
            wifi = connect_wifi()

        # --- always listen for commands, even before /start ---
        updates = get_updates()

        for update in updates:
            last_update_id = update["update_id"]

            if "message" in update and "text" in update["message"]:
                chat_id = update["message"]["chat"]["id"]
                user_text = update["message"]["text"].strip()
                command = user_text.split('@')[0]

                if command == "/start":
                    bot_started = True
                    send_message(
                        "Monitoring started. Use /status to read data.",
                        target_chat_id=chat_id,
                    )

                elif not bot_started:
                    # ignore all other commands until /start is received
                    send_message("Bot not started yet. Send /start first.", target_chat_id=chat_id)

                elif command == "/status":
                    try:
                        temp, hum = read_dht()
                        status_msg = f"System OK\nTemp: {temp:.2f} C\nHumi: {hum:.2f}% \nRelay State: {relay_state}"
                    except OSError:
                        status_msg = "Error: Could not read from DHT11 sensor."
                    send_message(status_msg, target_chat_id=chat_id)

                elif command == "/on":
                    toggle_relay_on()
                    send_message("Relay ON", target_chat_id=chat_id)

                elif command == "/off":
                    toggle_relay_off()
                    send_message("Relay OFF", target_chat_id=chat_id)

                else:
                    send_message("Unknown command. Try /start or /status.", target_chat_id=chat_id)

        # --- monitoring/alerts only run once bot_started is True ---
        if bot_started:
            temp, hum = read_dht()
            sensor_message = f"System OK\nTemp: {temp:.2f} C\nHumi: {hum:.2f}%"
            print(sensor_message)

            alert_message = alert(temp, relay_state)
            if alert_message is not None:
                send_message(alert_message)

        time.sleep(2)

    except Exception as e:
        print("Error in main loop:", e)
        time.sleep(5)
