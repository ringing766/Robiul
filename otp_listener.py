import asyncio
import json
import re
import time
from datetime import datetime
import pytz
import requests
import websockets

main_otp_bots = [
    "7080545849:AAEUiijbe1FKI_3AdiHkLutVV63wMKZU0xI"
]

CHAT_ID1 = "-1002601589640"
token = "eyJpdiI6ImFtaFc4eXlHcHR5..."  # Token shortened for privacy

ws_url = f"wss://ivasms.com:2087/socket.io/?token={requests.utils.quote(token)}&EIO=4&transport=websocket"

bot_index = {
    "otp": 0
}

def escape_html(text):
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#039;"))

COUNTRY_CODES = {
    "+880": ("Bangladesh", "🇧🇩"),
    "+91": ("India", "🇮🇳"),
    "+1": ("USA/Canada", "🇺🇸"),
    "+44": ("UK", "🇬🇧"),
    "+971": ("UAE", "🇦🇪"),
    "+92": ("Pakistan", "🇵🇰"),
    "+7": ("Russia/Kazakhstan", "🇷🇺"),
    "+98": ("Iran", "🇮🇷"),
    "+81": ("Japan", "🇯🇵"),
    "+61": ("Australia", "🇦🇺"),
    "+49": ("Germany", "🇩🇪"),
    "+33": ("France", "🇫🇷"),
    "+55": ("Brazil", "🇧🇷"),
}

def detect_country(number: str) -> str:
    number = number.strip()
    if not number.startswith("+"):
        number = "+" + number
    for code in sorted(COUNTRY_CODES.keys(), key=len, reverse=True):
        if number.startswith(code):
            name, flag = COUNTRY_CODES[code]
            return f"{flag} {name}"
    return "🏳️ Unknown"

def send_telegram(bot_type, chat_id, text):
    bots = main_otp_bots
    index = bot_index[bot_type]
    total = len(bots)
    tried = 0
    while tried < total:
        token = bots[index]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            print(f"✔️ Message sent to Telegram 📩 via Bot {index + 1}")
            bot_index[bot_type] = index
            return
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                print(f"⚠️ Rate limit on Bot {index + 1}, trying next bot...")
                index = (index + 1) % total
                tried += 1
                time.sleep(1.5)
            else:
                print("⚠️ Telegram HTTP error:", e)
                break
        except Exception as e:
            print("⚠️ Telegram error:", e)
            break
    print(f"🚫 All bots failed for {bot_type}")

async def main():
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                print("🖥️ Connected to IVASMS ✅")
                while True:
                    data = await ws.recv()
                    if data.startswith("0"):
                        await ws.send("40/livesms,")
                        continue
                    if data == "2":
                        await ws.send("3")
                        continue
                    json_start = data.find("[")
                    if json_start == -1:
                        continue
                    json_data_str = data[json_start:]
                    try:
                        payload = json.loads(json_data_str)
                    except json.JSONDecodeError:
                        continue
                    if len(payload) < 2:
                        continue
                    msg = payload[1]
                    bd_time = datetime.utcnow().astimezone(pytz.timezone('Asia/Dhaka')).strftime("%d/%m/%Y, %H:%M:%S")
                    recipient = msg.get('recipient', '')
                    country = detect_country(recipient)
                    otp_search = re.search(r"\b\d{4,}\b|\b\d{2,}-\d{2,}\b|\d{2,} \d{2,}\b", msg.get('message', ''))
                    otp = otp_search.group(0) if otp_search else "N/A"
                    text = (f"✨ <b>OTP Received</b> ✨\n\n"
                            f"⏰ <b>Time:</b> {bd_time}\n"
                            f"📞 <b>Number:</b> {recipient}\n"
                            f"🌍 <b>Country:</b> {country}\n"
                            f"🔧 <b>Service:</b> {msg.get('originator', 'N/A')}\n\n"
                            f"🔑 <b>OTP:</b> <code>{otp}</code>\n\n"
                            f"<blockquote>{escape_html(msg.get('message', ''))}</blockquote>")
                    send_telegram("otp", CHAT_ID1, text)
        except Exception as e:
            print(f"❌ Connection lost: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
