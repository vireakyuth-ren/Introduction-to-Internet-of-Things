## **Explanation of the program**

MicroPython project for ESP32: monitors temperature/humidity with a DHT11 sensor and controls a relay through a Telegram bot.

This is a small IoT project that uses an ESP32 and a DHT11 sensor to keep an eye on temperature and humidity, with a relay you can control remotely through Telegram. Instead of building a web dashboard, the project wired it up to a Telegram bot so you send commands like `/status` to check the readings, or `/on` and `/off` to control the relay directly from your phone. It also handles itself a bit: if the temperature climbs too high it sends an alert, and if the relay's on and things cool back down, it switches off automatically.

### **Hardware**
- ESP32
- DHT11 sensor → GPIO 4
- Relay → GPIO 2

### **Setup**
1. Flash MicroPython onto the ESP32.
2. Fill in your Wi-Fi and Telegram bot details at the top of the file:
```
python
   SSID = "your_wifi_name"
   PASSWORD = "your_wifi_password"
   BOT_TOKEN = "your_bot_token"
   CHAT_ID = "your_chat_id"
```

### **Telegram Commands**
- `/start` : Start monitoring
- `/status` :	Get current temp, humidity, relay state
- `/on`	: Turn relay ON
- `/off` : Turn relay OFF

### **Behavior**
- Alerts are only active after /start.
- If temp ≥ 28°C, sends an alert.
- If relay is ON and temp drops below 28°C, it auto-turns OFF.

## **Flowchart**
### How It Works

The bot runs a single loop that repeats every 2 seconds. It's structured in three stages:

### 1. Main loop

- The board connects to Wi-Fi, then sends a welcome message and waits.
- Each cycle, it first checks the Wi-Fi connection. If it's dropped, it reconnects and continues — the loop never gets stuck waiting on a connection.
- It then checks for new Telegram messages and handles any commands (see below).
- If monitoring has been started (`/start` was received), it also reads the sensor and checks for alerts.
- After all of that, it waits 2 seconds and repeats.

### 2. Command handling

Every incoming Telegram message is routed based on its text:

- `/start` — enables monitoring and confirms with a reply.
- Any other command sent **before** `/start` — the bot replies asking for `/start` first and ignores the command.
- Once started, `/status`, `/on`, and `/off` are handled individually: `/status` reads and reports the sensor, `/on`/`/off` toggle the relay directly.
- Anything else is treated as an unknown command.

### 3. Alert and relay logic

This runs automatically every cycle once monitoring is active, independent of any Telegram command:

- If the relay is **off** and temperature is still below 28°C — nothing happens.
- If the relay is **off** and temperature reaches 28°C or higher — the bot sends a text alert only. It does **not** turn the relay on automatically.
- If the relay is **on** and temperature drops below 28°C — the bot turns the relay off and sends an auto-off notification.
- If the relay is **on** and temperature is still high — nothing happens; it stays on.

In short: the relay only ever turns off automatically, never on. Turning it on is a manual action via `/on`.

[Demo video link](https://youtube.com/shorts/T2WVA4LPYaw?feature=share)
