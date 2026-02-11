import sys
import functools
print = functools.partial(print, flush=True)

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import pytz  # 시간대 설정을 위한 라이브러리 추가
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. 설정 (성민0106님의 새 독립 계정 키 적용)
# ==========================================
ALPACA_API_KEY = 'PKHQEN22KBWB2HSXRGMPWQ3QYL'
ALPACA_SECRET_KEY = 'ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i'
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

# Render 생존용 가짜 서버
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

def send_ntfy(message):
    try:
        requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=5)
    except:
        pass

def get_signal(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False, show_errors=False, timeout=10, include_prepost=True)
        if df.empty or len(df) < 20: return None
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        curr_price = float(df['Close'].iloc[-1])
        prev_rsi = float(df['RSI'].iloc[-2])
        curr_rsi = float(df['RSI'].iloc[-1])
        curr_vwap = float(df['VWAP'].iloc[-1])
        avg_vol = df['Volume'].iloc[-6:-1].mean()
        curr_vol = df['Volume'].iloc[-1]
        
        if prev_rsi < 35 and curr_rsi >= 35:
            if curr_price > curr_vwap and curr_vol > (avg_vol * 1.5):
                return round(curr_price, 2), curr_rsi
    except:
        return None
    return None

def buy_order_direct(ticker, price, rsi):
    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}
    qty = max(1, int(100 / price))
    data = {
        "symbol": ticker, "qty": str(qty), "side": "buy", "type": "market",
        "time_in_force": "gtc", "order_class": "bracket",
        "take_profit": {"limit_price": str(round(price * 1.05, 2))},
        "stop_loss": {"stop_price": str(round(price * 0.97, 2))}
    }
    try:
        res = requests.post(url, json=data, headers=headers, timeout=10)
        status = "성공" if res.status_code == 200 else f"실패({res.status_code})"
        msg = f"🚀 [sm2 포착] {ticker}\n가격: ${price}\nRSI: {rsi:.1f}\n결과: {status}"
        send_ntfy(msg)
        print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')}] {msg}")
    except:
        print(f"❌ {ticker} 주문 중 에러")

if __name__ == "__main__":
    KST = pytz.timezone('Asia/Seoul')
    print("🚀 sm2 가동 (한국 시간 기준 18:00 - 06:00)")
    send_ntfy("🚨 [sm2] 성민님, 한국 시간 고정 버전이 배포되었습니다!")

    while True:
        now = datetime.now(KST)
        if now.hour >= 18 or now.hour < 6:
            now_str = now.strftime('%H:%M:%S')
            print(f"⏰ {now_str} - 102개 종목 스캔 시작...")
            for ticker in tickers:
                signal = get_signal(ticker)
                if signal:
                    buy_order_direct(ticker, signal[0], signal[1])
                time.sleep(0.1)
            print(f"✨ {now_str} - 사이클 완료. 5분 대기.")
            time.sleep(300)
        else:
            print(f"💤 현재 한국 시간 {now.hour}시, 시장 휴식기입니다.")
            time.sleep(3600)
