import sys
import functools
# [강력 처방 1] 로그가 Render 화면에 즉시 찍히도록 강제 설정
print = functools.partial(print, flush=True)

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. 설정 (성민님 정보 - 정확히 입력됨)
# ==========================================
ALPACA_API_KEY = 'PKI4EKE6RY5VHXH7EM4VCP6TKG'
ALPACA_SECRET_KEY = '43YAJLe5CTQVE6pwHat6oDw3npughyRnCja1gsFX2eM3'
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

tickers = [
    "TTOO", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "TCBP", "MGIH", "WISA", "IMPP", 
    "GRI", "MRAI", "XFOR", "TENX", "MGRM", "NVOS", "CDIO", "ICU", "MTC", "BDRX", 
    "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "CYTO", "HOLO", "ICG", "IKT",
    "BNRG", "AITX", "BCEL", "BNGO", "VRAX", "ADTX", "APDN", "TRVN", "CRBP", "KNSA",
    "SCYX", "OPGN", "TNXP", "AGEN", "SELB", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE",
    "ADXS", "APTO", "ARAV", "AVDL", "BCLI", "CASI", "CLSD",
    "CTXR", "DRRX", "DYAI", "EBON", "ECOR", "GNPX", "HTGM", "IDRA", "KERN",
    "KMPH", "MBRX", "MTCR", "MYNZ", "NMTC", "ONDS", "OPCH", "OTIC", "PLIN", "PLXP",
    "PRPO", "QUIK", "RBBN", "SINT", "SNPX", "SQNS", "SYBX", "THMO", "TLSA", "VBLT",
    "VIVE", "VTGN", "WATT", "XERS", "ZVSA", "AQST", "ARQT", "ASRT",
    "BCRX", "BTX", "CHRS", "CTIC", "EVFM", "GEVO", "GNLN", "LPCN"
]

# ------------------------------------------
# [보호막 1] Render 생존용 가짜 서버
# ------------------------------------------
def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is Running!")
        def log_message(self, format, *args): return 
    server = HTTPServer(('0.0.0.0', 10000), Handler)
    server.serve_forever()
threading.Thread(target=run_dummy_server, daemon=True).start()

# ------------------------------------------
# [보호막 2] 안전한 알림 전송 (에러 시에도 봇 생존)
# ------------------------------------------
def send_ntfy(message):
    try:
        requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=5)
    except Exception as e:
        print(f"⚠️ 알람 전송 실패(무시): {e}")

# ------------------------------------------
# 매매 로직: RSI 35 골든크로스
# ------------------------------------------
def get_signal(ticker):
    try:
        # 데이터 수집 시 타임아웃 10초 설정 (무한 대기 방지)
        df = yf.download(ticker, period="1d", interval="5m", progress=False, show_errors=False, timeout=10)
        if df.empty or len(df) < 20: return None
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        prev_rsi = float(df['RSI'].iloc[-2])
        curr_rsi = float(df['RSI'].iloc[-1])
        curr_price = float(df['Close'].iloc[-1])
        
        if prev_rsi < 35 and curr_rsi >= 35:
            return round(curr_price, 2), curr_rsi
    except:
        return None
    return None

def buy_order_direct(ticker, price, rsi):
    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        "Content-Type": "application/json"
    }
    
    qty = max(1, int(100 / price))
    data = {
        "symbol": ticker, "qty": str(qty), "side": "buy", "type": "market",
        "time_in_force": "gtc", "order_class": "bracket",
        "take_profit": {"limit_price": str(round(price * 1.05, 2))},
        "stop_loss": {"stop_price": str(round(price * 0.97, 2))}
    }
    
    try:
        res = requests.post(url, json=data, headers=headers, timeout=10)
        status = "✅ 주문성공" if res.status_code == 200 else f"❌ 주문실패({res.status_code})"
        msg = f"🔎 [포착] {ticker}\n가격: ${price}\nRSI: {rsi:.1f}\n결과: {status}"
        send_ntfy(msg)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    except Exception as e:
        print(f"❌ {ticker} 주문 중 에러: {e}")

# ------------------------------------------
# 메인 루프 (실시간 로그 보고 버전)
# ------------------------------------------
if __name__ == "__main__":
    print("🚀 봇 가동 시퀀스 시작 (실시간 로그 모드)")
    send_ntfy("🚨 [융합 완료] 성민님, 봇이 무적 보호막을 입고 재가동되었습니다!")

    while True:
        now = datetime.now().strftime('%H:%M:%S')
        print(f"⏰ {now} - {len(tickers)}개 종목 분석 시작...")
        
        for ticker in tickers:
            signal = get_signal(ticker)
            if signal:
                price, rsi = signal
                buy_order_direct(ticker, price, rsi)
            # API 과부하 방지를 위한 미세 대기
            time.sleep(0.1)
                
        print(f"✨ {now} - 한 사이클 완료. 5분 대기합니다.")
        time.sleep(300)
        
