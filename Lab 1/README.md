**Explanation of the program**

MicroPython project for ESP32: monitors temperature/humidity with a DHT11 sensor and controls a relay through a Telegram bot.

This is a small IoT project that uses an ESP32 and a DHT11 sensor to keep an eye on temperature and humidity, with a relay you can control remotely through Telegram. Instead of building a web dashboard, the project wired it up to a Telegram bot so you send commands like /status to check the readings, or /on and /off to control the relay directly from your phone. It also handles itself a bit: if the temperature climbs too high it sends an alert, and if the relay's on and things cool back down, it switches off automatically.

**Hardware**
- ESP32
- DHT11 sensor → GPIO 4
- Relay → GPIO 2

**Setup**
1. Flash MicroPython onto the ESP32.
2. Fill in your Wi-Fi and Telegram bot details at the top of the file:
```
python
   SSID = "your_wifi_name"
   PASSWORD = "your_wifi_password"
   BOT_TOKEN = "your_bot_token"
   CHAT_ID = "your_chat_id"
```

**Telegram Commands**
- /start : Start monitoring
- /status :	Get current temp, humidity, relay state
- /on	: Turn relay ON
- /off : Turn relay OFF

**Behavior**
- Alerts are only active after /start.
- If temp ≥ 28°C, sends an alert.
- If relay is ON and temp drops below 28°C, it auto-turns OFF.

[Demo video link](https://youtube.com/shorts/T2WVA4LPYaw?feature=share)
