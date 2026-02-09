import yfinance as yf
import requests
import time
from flask import Flask
from threading import Thread
import os

# 1. 서버 설정 (UptimeRobot용)
app = Flask('')

@app.route('/')
def home():
    return "성민0106님의 로봇이 열일 중입니다!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# 2. 알람 설정
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

def send_ntfy(message):
    try:
        requests.post(NTFY_URL, data=message.encode('utf-8'))
    except:
        pass

# 3. 나스닥 감시 로직
def monitor_nasdaq():
    print("🚀 나스닥 감시 시작!")
    # 아래 주소를 UptimeRobot에 넣으세요
    print(f"📢 주소: https://{os.environ.get('REPL_SLUG')}.{os.environ.get('REPL_OWNER')}.repl.co")
    send_ntfy("✅ 나스닥 로봇 가동 시작!")

    while True:
        try:
            nasdaq = yf.Ticker("NQ=F")
            price = nasdaq.history(period="1d")['Close'].iloc[-1]
            print(f"현재가: {price}")
            
            # 테스트용: 10000보다 크면 무조건 알람 (작동 확인용)
            if price > 10000:
                send_ntfy(f"🚨 현재가: {price}")
            
            time.sleep(60) # 1분마다 체크
        except Exception as e:
            print(f"에러 재시도 중... {e}")
            time.sleep(10)

# ★★★ 이 부분이 사진에서 빠져있던 핵심입니다! ★★★
if __name__ == "__main__":
    keep_alive()
    monitor_nasdaq()
