import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. 설정 (키 확인 필수!)
# ==========================================
ALPACA_API_KEY = 'PKDAL2Z52D5YTI2V7N2TR2UXGO'
ALPACA_SECRET_KEY = '7odPStsrP7u931DN34UYsaYH1mJsUYZSo399uK3oHpHt'
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'
NTFY_URL = "https://ntfy.sh/sungmin_nasdaq_bot"

# 성민님의 '화끈한' 종목 리스트 (에러 나는 것들은 로봇이 알아서 패스함)
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
# Render 배포 오류 해결용 가짜 서버
# ------------------------------------------
def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is Running!")
    server = HTTPServer(('0.0.0.0', 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ------------------------------------------
# 매매 로직 (성민님 맞춤형)
# ------------------------------------------
def get_signal(ticker):
    try:
        # 데이터 가져오기 (오류 방지를 위해 에러 메시지 무시 설정)
        df = yf.download(ticker, period="1d", interval="5m", progress=False, show_errors=False)
        if df.empty or len(df) < 15: return None
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        last_price = float(df.iloc[-1]['Close'])
        last_rsi = float(df.iloc[-1]['RSI'])
        
        # 변동성 종목 특성상 RSI 45 이하일 때 적극 매수 시도
        if last_rsi <= 45:
            return round(last_price, 2)
    except:
        return None
    return None

def buy_order_direct(ticker, price):
    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        "Content-Type": "application/json"
    }
    # 한 종목당 $100치 매수
    qty = max(1, int(100 / price))
    
    data = {
        "symbol": ticker,
        "qty": str(qty),
        "side": "buy",
        "type": "market",
        "time_in_force": "gtc",
        "order_class": "bracket",
        "take_profit": {"limit_price": str(round(price * 1.05, 2))}, # 익절 5% (변동성 고려)
        "stop_loss": {"stop_price": str(round(price * 0.96, 2))}     # 손절 4% (변동성 고려)
    }
    
    try:
        res = requests.post(url, json=data, headers=headers)
        if res.status_code == 200:
            msg = f"🚀 [매수성공] {ticker}\n가격: ${price} / 수량: {qty}주"
        else:
            msg = f"❌ [주문실패] {ticker}: {res.text}"
        print(msg)
        requests.post(NTFY_URL, data=msg.encode('utf-8'))
    except:
        pass

# 메인 루프
print(f"🤖 성민0106님, 총 {len(tickers)}개 종목 감시를 시작합니다!")
while True:
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} 전 종목 스캔 중...")
    for ticker in tickers:
        price = get_signal(ticker)
        if price:
            buy_order_direct(ticker, price)
            time.sleep(1) # API 과부하 방지
    time.sleep(600) # 10분마다 반복


        
