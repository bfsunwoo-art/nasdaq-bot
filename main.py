import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. 설정 (성민님 정보 - 정확히 입력하세요!)
# ==========================================
ALPACA_API_KEY = 'PKDAL2Z52D5YTI2V7N2TR2UXGO'
ALPACA_SECRET_KEY = '7odPStsrP7u931DN34UYsaYH1mJsUYZSo399uK3oHpHt'
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

# 성민님의 '폭풍의 눈' 감시 종목 리스트
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
# Render 배포 에러 방지용 가짜 서버 (로그 청소 버전)
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
        def log_message(self, format, *args): return # 지저분한 501 에러 숨김
    
    server = HTTPServer(('0.0.0.0', 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ------------------------------------------
# 매매 로직: 성민님의 RSI 35 골든크로스 전략
# ------------------------------------------
def get_signal(ticker):
    try:
        # 최근 데이터를 가져옴 (최소 20개 이상의 봉 필요)
        df = yf.download(ticker, period="1d", interval="5m", progress=False, show_errors=False)
        if df.empty or len(df) < 20: return None
        
        # RSI 지표 계산 (기간 14)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 이전 봉과 현재 봉의 RSI 값 추출
        prev_rsi = float(df['RSI'].iloc[-2])
        curr_rsi = float(df['RSI'].iloc[-1])
        curr_price = float(df['Close'].iloc[-1])
        
        # [성민님 핵심 조건]: RSI가 35 미만에서 35 이상으로 뚫고 올라갈 때!
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
    
    # 설정: 한 종목당 $100 투자 / 익절 5% / 손절 3%
    qty = max(1, int(100 / price))
    take_profit = round(price * 1.05, 2)
    stop_loss = round(price * 0.97, 2)

    data = {
        "symbol": ticker,
        "qty": str(qty),
        "side": "buy",
        "type": "market",
        "time_in_force": "gtc",
        "order_class": "bracket",
        "take_profit": {"limit_price": str(take_profit)},
        "stop_loss": {"stop_price": str(stop_loss)}
    }
    
    try:
        res = requests.post(url, json=data, headers=headers)
        status = "✅ 주문성공" if res.status_code == 200 else f"❌ 주문실패({res.status_code})"
        
        # ntfy 알림 전송
        msg = f"🔎 [포착] {ticker}\n가 격: ${price}\nRSI: {rsi:.1f}\n결 과: {status}"
        requests.post(NTFY_URL, data=msg.encode('utf-8'))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    except Exception as e:
        print(f"주문 에러: {e}")

# ------------------------------------------
# 메인 루프 (무한 반복)
# ------------------------------------------
# 시작 알림
requests.post(NTFY_URL, data="🤖 성민0106님, '폭풍의 눈' 감시 봇이 가동되었습니다!".encode('utf-8'))

while True:
    now_time = datetime.now().strftime('%H:%M:%S')
    print(f"⏰ {now_time} 전 종목 분석 시작...")
    
    for ticker in tickers:
        signal = get_signal(ticker)
        if signal:
            price, rsi = signal
            buy_order_direct(ticker, price, rsi)
            time.sleep(0.5) # API 호출 제한 방지
            
    print(f"✨ 스캔 완료. 5분 후 다시 시작합니다.")
    time.sleep(300) # 5분 간격 스캔 (골든크로스를 놓치지 않기 위해 단축)

        
