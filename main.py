import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home(): return "성민0106 v4.0 트레이더 봇 가동중"

def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.daemon = True
    t.start()

NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=15)
    except: pass

# --- [시총 1000억 미만 소형주/바이오 리스트] ---
WATCH_LIST = [
    "TTOO", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "TCBP", "MGIH", "WISA", "IMPP", 
    "GRI", "MRAI", "XFOR", "TENX", "MGRM", "NVOS", "CDIO", "ICU", "MTC", "BDRX", 
    "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "CYTO", "HOLO", "ICG", "IKT",
    "BNRG", "AITX", "BCEL", "BNGO", "VRAX", "ADTX", "APDN", "TRVN", "CRBP", "KNSA",
    "SCYX", "OPGN", "TNXP", "AGEN", "SELB", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE",
    "ADXS", "APTO", "ARAV", "AVDL", "AXDX", "BCLI", "BIOL", "BSGM", "CASI", "CLSD",
    "CTXR", "DRRX", "DYAI", "EBON", "ECOR", "EYEN", "GNPX", "HTGM", "IDRA", "KERN",
    "KMPH", "MBRX", "MTCR", "MYNZ", "NMTC", "ONDS", "OPCH", "OTIC", "PLIN", "PLXP",
    "PRPO", "QUIK", "RBBN", "SINT", "SNPX", "SQNS", "SYBX", "THMO", "TLSA", "VBLT",
    "VIVE", "VTGN", "WATT", "XERS", "ZOM", "ZVSA", "AALX", "AQST", "ARQT", "ASRT",
    "BCRX", "BTX", "CHRS", "CTIC", "EVFM", "GEVO", "GNLN", "IDEX", "IDRA", "LPCN"
]

def get_nasdaq_status():
    """나스닥 지수 흐름 파악 (시장 리스크 체크)"""
    try:
        ndq = yf.Ticker("^IXIC")
        hist = ndq.history(period="2d")
        change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
        return round(change, 2)
    except: return 0

def scan_integrated_system():
    MAX_MARKET_CAP = 75000000 # 약 1000억
    nasdaq_change = get_nasdaq_status()
    
    print(f"\n🔎 [v4.0] 지수 현황: {nasdaq_change}% | 분석 시작...", flush=True)
    
    for ticker in WATCH_LIST:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            market_cap = info.get('marketCap', 0)
            
            if market_cap == 0 or market_cap > MAX_MARKET_CAP: continue

            df = stock.history(period="60d") # 지표 계산을 위해 60일 데이터
            if len(df) < 30: continue

            # 1. RSI 계산 (광기 판별기)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            current_rsi = round(df['RSI'].iloc[-1], 1)

            # 2. 거래량 및 변동성 (폭풍의 눈 조건)
            avg_vol_20 = df['Volume'].iloc[-21:-1].mean()
            max_vol_3d = df['Volume'].iloc[-3:].max()
            high_20 = df['High'].iloc[-20:].max()
            low_20 = df['Low'].iloc[-20:].min()
            volatility = (high_20 - low_20) / low_20
            current_price = df['Close'].iloc[-1]

            # 3. 매물대 체크 (최근 40일 최고점 돌파 여부)
            is_breakout = current_price >= df['High'].iloc[-40:-1].max()

            # --- 포착 로직 ---
            is_volume_spike = (avg_vol_20 > 0) and (max_vol_3d >= (avg_vol_20 * 2.0))
            is_sideways = volatility <= 0.25
            
            # 1. NaN 데이터 및 필수 조건 검사 (가장 중요!)
            if pd.isna(current_rsi) or avg_vol_20 <= 0:
                continue
            
            if is_volume_spike and is_sideways:
                # RSI에 따른 상태 진단
                if current_rsi >= 80: rsi_status = "⚠️ 광기(설거지주의)"
                elif current_rsi >= 60: rsi_status = "🔥 상승탄력"
                else: rsi_status = "✅ 초기진입유리"

                # 지수 상황에 따른 멘트
                market_msg = "🟢 장세양호" if nasdaq_change > -1 else "🔴 지수급락주의"

                entry_price = round(current_price, 3)
                target_price = round(entry_price * 1.20, 3)
                stop_loss = round(entry_price * 0.90, 3)

                msg = (f"🌪️ [v4.0 폭풍의눈 포착!]\n"
                       f"종목: {ticker} (${round(market_cap/1000000, 1)}M)\n"
                       f"상태: {rsi_status} | {market_msg}\n"
                       f"------------------\n"
                       f"🚩 진입: {entry_price}\n"
                       f"🎯 목표: {target_price} (+20%)\n"
                       f"🛡️ 손절: {stop_loss} (-10%)\n"
                       f"------------------\n"
                       f"📊 RSI: {current_rsi} | 돌파: {'YES' if is_breakout else 'NO'}\n"
                       f"📈 거래: {round(max_vol_3d/avg_vol_20, 1)}배 | 변동: {round(volatility*100, 1)}%")

                send_ntfy(msg)
                print(f"✅ 포착: {ticker} (RSI: {current_rsi})", flush=True)

        except: continue
    print("✨ 스캔 완료. 30분 후 재시작.", flush=True)

if __name__ == "__main__":
    keep_alive()
    while True:
        scan_integrated_system()
        time.sleep(1800)



        
