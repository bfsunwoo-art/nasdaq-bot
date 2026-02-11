import sys
import functools
# [강력 처방] 로그 실시간 출력 설정
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
# 1. 설정 (새로 만드신 독립 계정 키를 꼭 확인하세요!)
# ==========================================
ALPACA_API_KEY = 'PKHQEN22KBWB2HSXRGMPWQ3QYL' # <- 새 계정 키로 확인 완료
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

# ------------------------------------------
# 매매 로직: RSI 35 + VWAP + Volume 필터 (프리마켓 대응)
# ------------------------------------------
def get_signal(ticker):
    try:
        # include_prepost=True로 프리마켓 데이터까지 수집
        df = yf.download(ticker, period="1d", interval="5m", progress=False, show_errors=False, timeout=10, include_prepost=True)
        if df.empty or len(df) < 20: return None
        
        # 1. RSI 계산
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 2. VWAP 계산 (수동 계산 또는 pandas_ta 활용)
        # VWAP = 합계(가격 * 거래량) / 합계(거래량)
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        
        curr_price = float(df['Close'].iloc[-1])
        prev_rsi = float(df['RSI'].iloc[-2])
        curr_rsi = float(df['RSI'].iloc[-1])
        curr_vwap = float(df['VWAP'].iloc[-1])
        
        # 거래량 필터: 최근 5개 봉(25분) 평균 거래량 대비 1.5배 터졌는지 확인
        avg_vol = df['Volume'].iloc[-6:-1].mean()
        curr_vol = df['Volume'].iloc[-1]
        
        # [최종 조건]
        # 1. RSI 35 골든크로스 (바닥 탈출)
        # 2. 현재가가 VWAP보다 위 (상승 추세)
        # 3. 거래량이 평균보다 1.5배 이상 (수급 확인)
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
        msg = f"🚀 [프리마켓/본장 포착] {ticker}\n가격: ${price}\nRSI: {rsi:.1f}\n결과: {status}"
        send_ntfy(msg)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    except:
        print(f"❌ {ticker} 주문 중 에러")

# ------------------------------------------
# 메인 스케줄러 (한국 시간 기준)
# ------------------------------------------
if __name__ == "__main__":
    print("🚀 봇 통합 가동 시퀀스 시작 (PM 18:00 - AM 06:00)")
    send_ntfy("🚨 [시즌 2] 성민님, 프리마켓+본장 통합 봇이 가동되었습니다!")

    while True:
        now = datetime.now()
        # 한국 시간 기준: 18시(오후 6시)부터 다음날 아침 06시까지 작동
        if now.hour >= 18 or now.hour < 6:
            now_str = now.strftime('%H:%M:%S')
            print(f"⏰ {now_str} - 102개 종목 통합 스캔 시작...")
            for ticker in tickers:
                signal = get_signal(ticker)
                if signal:
                    buy_order_direct(ticker, signal[0], signal[1])
                time.sleep(0.1)
            print(f"✨ {now_str} - 사이클 완료. 5분 대기.")
            time.sleep(300)
        else:
            # 낮 시간엔 1시간마다 체크하며 대기
            print(f"💤 현재 시간 {now.hour}시, 시장 휴식기입니다. 1시간 뒤 확인.")
            time.sleep(3600)
