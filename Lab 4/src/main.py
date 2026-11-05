import network, time, ujson
from umqtt.simple import MQTTClient
from machine import Pin, I2C, SoftI2C, ADC
from bmp280 import BMP280


# Fill WIFI credentials
SSID = ""
PASSWORD = ""            

BROKER = "broker.hivemq.com"  # You can use this broker, it's the same one that I use
PORT = 1883
CLIENT_ID = b""               # Fill your client ID
TOPIC = b""                   # Fill with your own topic
KEEPALIVE = 30

# ---------- Edge logic settings ----------
PUBLISH_INTERVAL = 2          # seconds
AVG_WINDOW = 5                # moving average samples (gas)
GAS_WARN = 2100               # >= 2100 -> WARNING
GAS_DANGER = 2600             # >= 2600 -> DANGER
FEVER_THRESHOLD = 32.5        # deg C

# ---------- I2C addresses ----------
MLX_ADDR = 0x5A
RTC_ADDR = 0x68


# ---------- Helpers ----------
class MLX90614:
    def __init__(self, i2c, addr=MLX_ADDR):
        self.i2c = i2c
        self.addr = addr

    def _read(self, reg):
        d = self.i2c.readfrom_mem(self.addr, reg, 3)
        return (d[1] << 8 | d[0]) * 0.02 - 273.15

    def ambient(self):
        return self._read(0x06)

    def object(self):
        return self._read(0x07)


class DS3231:
    def __init__(self, i2c, addr=RTC_ADDR):
        self.i2c = i2c
        self.addr = addr

    @staticmethod
    def _bcd2dec(b):
        return (b >> 4) * 10 + (b & 0x0F)

    @staticmethod
    def _dec2bcd(d):
        return ((d // 10) << 4) | (d % 10)

    def datetime(self):
        d = self.i2c.readfrom_mem(self.addr, 0x00, 7)
        sec = self._bcd2dec(d[0] & 0x7F)
        minute = self._bcd2dec(d[1])
        hour = self._bcd2dec(d[2] & 0x3F)
        day = self._bcd2dec(d[4])
        month = self._bcd2dec(d[5] & 0x1F)
        year = self._bcd2dec(d[6]) + 2000
        return (year, month, day, hour, minute, sec)

    def set_datetime(self, year, month, day, hour, minute, sec, weekday=1):
        buf = bytearray([
            self._dec2bcd(sec), self._dec2bcd(minute), self._dec2bcd(hour),
            self._dec2bcd(weekday), self._dec2bcd(day),
            self._dec2bcd(month), self._dec2bcd(year - 2000)
        ])
        self.i2c.writeto_mem(self.addr, 0x00, buf)

    def timestamp(self):
        y, mo, d, h, mi, s = self.datetime()
        return "%04d-%02d-%02d %02d:%02d:%02d" % (y, mo, d, h, mi, s)


class MovingAverage:
    def __init__(self, size):
        self.size = size
        self.buf = []

    def add(self, v):
        self.buf.append(v)
        if len(self.buf) > self.size:
            self.buf.pop(0)
        return sum(self.buf) / len(self.buf)


def classify_gas(avg):
    """Returns (risk_level, risk_code)"""
    if avg >= GAS_DANGER:
        return "DANGER", 2
    if avg >= GAS_WARN:
        return "WARNING", 1
    return "SAFE", 0


# ---------- Wi-Fi / MQTT ----------
def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)
        t0 = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 20000:
                raise RuntimeError("Wi-Fi connect timeout")
            time.sleep(0.3)
    print("WiFi OK:", wlan.ifconfig())
    return wlan


def make_client():
    return MQTTClient(client_id=CLIENT_ID, server=BROKER, port=PORT, keepalive=KEEPALIVE)


def connect_mqtt(c):
    time.sleep(0.5)
    c.connect()
    print("MQTT connected")


def main():
    wifi_connect()

    # Separate I2C bus (own pins) for each sensor
    i2c_bmp = I2C(0, scl=Pin(22), sda=Pin(21))                 # BMP280
    i2c_rtc = I2C(1, scl=Pin(19), sda=Pin(18))                 # DS3231
    i2c_mlx = SoftI2C(scl=Pin(26), sda=Pin(25), freq=100000)   # MLX90614

    print("BMP280 bus:", [hex(a) for a in i2c_bmp.scan()])
    print("DS3231 bus:", [hex(a) for a in i2c_rtc.scan()])
    print("MLX90614 bus:", [hex(a) for a in i2c_mlx.scan()])

    bmp = BMP280(i2c_bmp)
    mlx = MLX90614(i2c_mlx)
    rtc = DS3231(i2c_rtc)

    # Run once to set the RTC, then comment out again:
    # rtc.set_datetime(2026, 10, 27, 14, 30, 0)

    # MQ-5 analog output on GPIO34, 12-bit ADC (0-4095)
    mq5 = ADC(Pin(34))
    mq5.atten(ADC.ATTN_11DB)
    mq5.width(ADC.WIDTH_12BIT)

    gas_avg_filter = MovingAverage(AVG_WINDOW)

    client = make_client()

    while True:
        try:
            connect_mqtt(client)
            while True:
                # --- Task 1: gas moving average ---
                gas_raw = mq5.read()
                gas_avg = round(gas_avg_filter.add(gas_raw), 1)
                print("Gas raw:", gas_raw, "| Gas avg:", gas_avg)

                # --- Task 2: risk classification (on averaged value) ---
                risk_level, risk_code = classify_gas(gas_avg)

                # --- Task 3: fever detection ---
                try:
                    body_temp = round(mlx.object(), 2)
                except OSError:
                    body_temp = None
                fever_flag = 1 if (body_temp is not None and body_temp >= FEVER_THRESHOLD) else 0

                data = {
                    "timestamp": rtc.timestamp(),
                    "gas_raw": gas_raw,
                    "gas_avg": gas_avg,
                    "risk_level": risk_level,
                    "risk_code": risk_code,
                    "body_temp": body_temp,
                    "fever_flag": fever_flag,
                    "pressure": round(bmp.pressure / 100, 2),   # hPa
                    "altitude": round(bmp.altitude, 2)          # meters
                }

                msg = ujson.dumps(data)
                client.publish(TOPIC, msg)

                print("Sent:", msg)
                time.sleep(PUBLISH_INTERVAL)

        except OSError as e:
            print("MQTT error:", e)
            try:
                client.close()
            except:
                pass
            print("Retrying MQTT in 3s...")
            time.sleep(3)
            try:
                wifi_connect()
            except RuntimeError as err:
                print(err)


main()