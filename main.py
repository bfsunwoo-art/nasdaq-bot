import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import alpaca_trade_api as tradeapi

# ==========================================
# 1. 설정 (이 부분을 성민님 정보로 수정하세요)
# ==========================================
ALPACA_API_KEY = 'PKDAL2Z52D5YTI2V7N2TR2UXGO'
ALPACA_SECRET_KEY = '7odPStsrP7u931DN34UYsaYH1mJsUYZSo399uK3oHpHt'
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets' # 모의투자용 주소

NTFY_URL = "https://ntfy.sh/sungmin_nasdaq_bot" # 성민님의 ntfy 주소

# 매매 설정
INVEST_AMOUNT = 100  # 한 종목당 투자할 금액 ($100)
TAKE_PROFIT = 0.03   # 익절 라인 (3%)
STOP_LOSS = 0.02     # 손절 라인 (2%)

# Alpaca API 연결
api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL, api_version='v2')

# 나스닥 100 + 주요 종목 리스트 (예시로 10개만 넣었으나 기존 리스트 그대로 쓰셔도 됩니다)
tickers =  ["TTOO", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "TCBP", "MGIH", "WISA", "IMPP", 
    "GRI", "MRAI", "XFOR", "TENX", "MGRM", "NVOS", "CDIO", "ICU", "MTC", "BDRX", 
    "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "CYTO", "HOLO", "ICG", "IKT",
    "BNRG", "AITX", "BCEL", "BNGO", "VRAX", "ADTX", "APDN", "TRVN", "CRBP", "KNSA",
    "SCYX", "OPGN", "TNXP", "AGEN", "SELB", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE",
    "ADXS", "APTO", "ARAV", "AVDL", "BCLI", "CASI", "CLSD",
    "CTXR", "DRRX", "DYAI", "EBON", "ECOR", "GNPX", "HTGM", "IDRA", "KERN",
    "KMPH", "MBRX", "MTCR", "MYNZ", "NMTC", "ONDS", "OPCH", "OTIC", "PLIN", "PLXP",
    "PRPO", "QUIK", "RBBN", "SINT", "SNPX", "SQNS", "SYBX", "THMO", "TLSA", "VBLT",
    "VIVE", "VTGN", "WATT", "XERS", "ZVSA", "AQST", "ARQT", "ASRT",
    "BCRX", "BTX", "CHRS", "CTIC", "EVFM", "GEVO", "GNLN", "IDRA", "LPCN" ]

def get_signal(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False)
        if len(df) < 20: return None
        
        # 지표 계산 (RSI, EMA)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['EMA20'] = ta.ema(df['Close'], length=20)
        
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        current_price = last_row['Close']

        # 매수 조건: RSI 30 이하에서 탈출 + EMA20 돌파 시도 등 (성민님 기존 로직 유지 가능)
        if prev_row['RSI'] < 35 and last_row['RSI'] >= 35:
            return round(float(current_price), 2)
    except:
        return None

def buy_order(ticker, price):
    try:
        # 1. 수량 계산 (금액 / 현재가)
        qty = max(1, int(INVEST_AMOUNT / price))
        
        # 2. 익절/손절가 계산
        tp_price = round(price * (1 + TAKE_PROFIT), 2)
        sl_price = round(price * (1 - STOP_LOSS), 2)

        # 3. 브래킷 주문 (매수 + 익절예약 + 손절예약) 전송
        api.submit_order(
            symbol=ticker,
            qty=qty,
            side='buy',
            type='market',
            time_in_force='gtc',
            order_class='bracket',
            take_profit={'limit_price': tp_price},
            stop_loss={'stop_price': sl_price}
        )
        
        msg = f"🚀 [매수완료] {ticker}\n수량: {qty}주 / 가격: ${price}\n🎯 익절가: ${tp_price}\n🛑 손절가: ${sl_price}"
        print(msg)
        requests.post(NTFY_URL, data=msg.encode('utf-8'))
        
    except Exception as e:
        error_msg = f"❌ [주문실패] {ticker}: {e}"
        print(error_msg)
        requests.post(NTFY_URL, data=error_msg.encode('utf-8'))

# 메인 루프
print("🤖 성민0106님의 자동매매 봇 가동 시작...")
while True:
    now = datetime.now()
    # 미국 시장 시간 확인 (22:30 ~ 05:00 KST 등 설정 가능)
    print(f"⏰ 현재 시간: {now.strftime('%H:%M:%S')} - 종목 스캔 중...")
    
    for ticker in tickers:
        entry_price = get_signal(ticker)
        if entry_price:
            buy_order(ticker, entry_price)
            time.sleep(1) # 주문 간격
            
    time.sleep(300) # 5분마다 반복



        
