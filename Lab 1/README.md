Explanation of the program

MicroPython project for ESP32: monitors temperature/humidity with a DHT11 sensor and controls a relay through a Telegram bot.

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
