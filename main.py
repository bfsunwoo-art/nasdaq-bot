import yfinance as yf
import pandas as pd
import requests
import time
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home(): return "폭풍의눈 감시 시스템 가동중"

def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.daemon = True
    t.start()

NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'))
    except: pass

# 감시할 종목 리스트 (시총이 작은 중소형주 위주로 계속 추가하세요)
# 예시: 미국 소형주들
WATCH_LIST = ["TTOO", "MULN", "GWAV", "FFIE", "BNSO", "SISI", "LUNR", "BBAI"] 

def scan_storm_eye():
    print("🚀 [시총 1000억 미만] 폭풍의 눈 스캔 시작...")
    for ticker in WATCH_LIST:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 1. 시가총액 필터 (1,000억 미만 = 약 7,500만 달러)
            market_cap = info.get('marketCap', 0)
            if market_cap == 0 or market_cap > 75000000:
                continue

            df = stock.history(period="40d")
            if len(df) < 30: continue

            # 2. 거래량 조건 (최근 3일 최대 vs 20일 평균)
            avg_vol_20 = df['Volume'].iloc[-21:-1].mean()
            max_vol_3d = df['Volume'].iloc[-3:].max()
            
            # 3. 횡보 조건 (20일 변동폭 15% 이내)
            high_20 = df['High'].iloc[-20:].max()
            low_20 = df['Low'].iloc[-20:].min()
            volatility = (high_20 - low_20) / low_20

            # 4. 정배열 확인 (현재가 > 20일 이평선)
            ma20 = df['Close'].iloc[-20:].mean()
            current_price = df['Close'].iloc[-1]

            # 최종 조건 검사
            is_volume_spike = max_vol_3d >= (avg_vol_20 * 3)
            is_tight_sideways = volatility <= 0.15 
            is_above_ma = current_price > ma20

            if is_volume_spike and is_tight_sideways and is_above_ma:
                msg = (f"🌪️ [폭풍의눈 포착!]\n"
                       f"종목: {ticker}\n"
                       f"시총: 약 {round(market_cap/1000000, 1)}M 달러\n"
                       f"거래량: {round(max_vol_3d/avg_vol_20, 1)}배 폭증\n"
                       f"변동폭: {round(volatility*100, 1)}% (초강력 응축)")
                send_ntfy(msg)
                print(f"✅ 포착 성공: {ticker}")

        except Exception as e:
            print(f"Error scanning {ticker}: {e}")

if __name__ == "__main__":
    keep_alive()
    while True:
        scan_storm_eye()
        # 소형주는 변동이 빠르니 30분마다 스캔하도록 변경
        time.sleep(1800)
