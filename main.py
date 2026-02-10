import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. 설정 (성민님 정보)
# ==========================================
ALPACA_API_KEY = 'PKDAL2Z52D5YTI2V7N2TR2UXGO'
ALPACA_SECRET_KEY = '7odPStsrP7u931DN34UYsaYH1mJsUYZSo399uK3oHpHt'
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
# [보호막 1] 알람 전송 함수 (에러가 나도 봇이 죽지 않음)
# ------------------------------------------
def send_ntfy(message):
    try:
        requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=10)
    except Exception as e:
        # 알람 전송에 실패해도 로그만 남기고 프로그램은 계속 진행합니다.
        print(f"⚠️ 알람 전송 실패 (무시하고 계속): {e}")

# ------------------------------------------
# Render 배포 에러 방지용 가짜 서버
# ------------------------------------------
def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is Running!")
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()
        def log_message(self, format, *args): return 
    
    server = HTTPServer(('0.0.0.0', 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ------------------------------------------
# 매매 로직: RSI 35 골든크로스
# ------------------------------------------
def get_signal(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False, show_errors=False)
        if df.empty or len(df) < 20: return None
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        prev_rsi = float(df['RSI'].iloc[-2])
        curr_rsi = float(df['RSI'].iloc[-1])
        curr_price = float(df['Close'].iloc[-1])
        
        # 성민님 핵심 조건: 35 돌파
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
    take_profit = round(price * 1.05, 2)
    stop_loss = round(price * 0.97, 2)

    data = {
        "symbol": ticker, "qty": str(qty), "side": "buy", "type": "market",
        "time_in_force": "gtc", "order_class": "bracket",
        "take_profit": {"limit_price": str(take_profit)},
        "stop_loss": {"stop_price": str(stop_loss)}
    }
    
    try:
        res = requests.post(url, json=data, headers=headers)
        status = "✅ 주문성공" if res.status_code == 200 else f"❌ 주문실패({res.status_code})"
        
        msg = f"🔎 [포착] {ticker}\n가 격: ${price}\nRSI: {rsi:.1f}\n결 과: {status}"
        send_ntfy(msg) # 보호막이 있는 알람 함수 사용
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    except Exception as e:
        print(f"주문 에러: {e}")

# ------------------------------------------
# 메인 루프 (보호막 적용)
# ------------------------------------------
if __name__ == "__main__":
    print("🚀 봇 가동 시퀀스 시작...")
    
    # 가동 알림 시도 (실패해도 무관함)
    send_ntfy("🤖 성민0106님, '폭풍의 눈' 감시 봇이 안전하게 재가동되었습니다!")

    while True:
        now = datetime.now().strftime('%H:%M:%S')
        print(f"⏰ {now} 분석 시작...")
        
        for ticker in tickers:
            result = get_signal(ticker)
            if result:
                price, rsi = result
                buy_order_direct(ticker, price, rsi)
                time.sleep(0.5)
                
        print(f"✨ {now} 스캔 완료. 5분 대기...")
        time.sleep(300)
        
