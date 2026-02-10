import yfinance as yf
import pandas as pd
import requests
import time
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home(): return "성민0106 소형바이오+폭풍의눈 v3.1 가동중"

def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.daemon = True
    t.start()

NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=15)
    except: pass

# --- [시총 1000억 미만 위주의 바이오 및 소형주 리스트] ---
WATCH_LIST = [
    "TTOO", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "TCBP", "MGIH", "WISA", "IMPP", 
    "GRI", "MRAI", "XFOR", "TENX", "MGRM", "NVOS", "CDIO", "ICU", "MTC", "BDRX", 
    "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "CYTO", "HOLO", "ICG", "IKT",
    "BNRG", "AITX", "BCEL", "BNGO", "VRAX", "ADTX", "APDN", "TRVN", "CRBP", "KNSA",
    "SCYX", "OPGN", "TNXP", "AGEN", "SELB", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE"
]

def analyze_bio_news(ticker):
    """바이오 관련 FDA/임상 키워드 실시간 분석"""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        for item in news[:5]:
            title = item['title'].upper()
            # 굵직한 바이오 키워드 필터링
            if any(word in title for word in ["FDA", "PHASE", "APPROVAL", "CLINICAL", "TRIAL", "PDUFA", "IND"]):
                return f"🔬 [이슈]: {item['title'][:55]}..."
        return None
    except: return None

def scan_integrated_system():
    # 시총 1000억 기준 (약 75,000,000 달러)
    MAX_MARKET_CAP = 75000000 
    
    print(f"\n🔎 [v3.1] 시총 1000억 미만 집중 분석 시작...", flush=True)
    for ticker in WATCH_LIST:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            market_cap = info.get('marketCap', 0)
            
            # 1. 시가총액 1,000억 미만 필터링 (가장 중요한 필터)
            if market_cap == 0 or market_cap > MAX_MARKET_CAP:
                continue

            df = stock.history(period="40d")
            if len(df) < 25: continue

            # 2. 폭풍의 눈 조건 계산 (거래량 2배, 변동폭 22%)
            avg_vol_20 = df['Volume'].iloc[-21:-1].mean()
            max_vol_3d = df['Volume'].iloc[-3:].max()
            high_20 = df['High'].iloc[-20:].max()
            low_20 = df['Low'].iloc[-20:].min()
            volatility = (high_20 - low_20) / low_20
            current_price = df['Close'].iloc[-1]

            # 3. 뉴스 데이터 기반 바이오 이슈 체크
            bio_issue = analyze_bio_news(ticker)

            # 포착 조건: (폭풍의눈 기술적 조건) OR (바이오 이슈 발견)
            is_storm_eye = (max_vol_3d >= avg_vol_20 * 2.0) and (volatility <= 0.22)
            
            if is_storm_eye or bio_issue:
                # 진입/익절/손절가 기계적 계산
                entry_price = round(current_price, 3)
                target_price = round(entry_price * 1.20, 3) # 바이오는 변동성이 크므로 +20% 목표
                stop_loss = round(entry_price * 0.90, 3)    # -10% 손절라인

                tag = "🌪️ 폭풍의눈" if is_storm_eye else "🧪 바이오특보"
                
                msg = (f"[{tag} 포착!]\n"
                       f"종목: {ticker} (시총: ${round(market_cap/1000000, 1)}M)\n"
                       f"------------------\n"
                       f"🚩 진입가: {entry_price}\n"
                       f"🎯 목표가: {target_price} (+20%)\n"
                       f"🛡️ 손절가: {stop_loss} (-10%)\n"
                       f"------------------\n")
                
                if bio_issue: msg += f"{bio_issue}\n"
                if is_storm_eye: msg += f"📊 거래량 {round(max_vol_3d/avg_vol_20, 1)}배 / 변동 {round(volatility*100, 1)}%"

                send_ntfy(msg)
                print(f"✅ 알람 전송 완료: {ticker}", flush=True)

        except: continue
    print("✨ 스캔 완료. 30분 후 다시 뒤집니다.", flush=True)

if __name__ == "__main__":
    keep_alive()
    while True:
        scan_integrated_system()
        time.sleep(1800)




        
