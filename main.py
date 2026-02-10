import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime

# ==========================================
# 1. 설정 (성민님 정보 입력)
# ==========================================
ALPACA_API_KEY = 'PKDAL2Z52D5YTI2V7N2TR2UXGO'
ALPACA_SECRET_KEY = '7odPStsrP7u931DN34UYsaYH1mJsUYZSo399uK3oHpHt'
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'

NTFY_URL = "https://ntfy.sh/sungmin_nasdaq_bot"

INVEST_AMOUNT = 100 
TAKE_PROFIT = 0.03   
STOP_LOSS = 0.02     

# 나스닥 주요 종목
tickers = [ "TTOO", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "TCBP", "MGIH", "WISA", "IMPP", 
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
        df['RSI'] = ta.rsi(df['Close'], length=14)
        last_row = df.iloc[-1]
        # 테스트를 위해 조건을 널널하게 잡음 (RSI 50 이하)
        if last_row['RSI'] <= 50:
            return round(float(last_row['Close']), 2)
    except:
        return None

def buy_order_direct(ticker, price):
    # Alpaca API에 직접 주문 요청 (라이브러리 미사용 방식)
    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        "Content-Type": "application/json"
    }
    
    qty = max(1, int(INVEST_AMOUNT / price))
    tp_price = round(price * (1 + TAKE_PROFIT), 2)
    sl_price = round(price * (1 - STOP_LOSS), 2)

    data = {
        "symbol": ticker,
        "qty": str(qty),
        "side": "buy",
        "type": "market",
        "time_in_force": "gtc",
        "order_class": "bracket",
        "take_profit": {"limit_price": str(tp_price)},
        "stop_loss": {"stop_price": str(sl_price)}
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            msg = f"🚀 [매수완료] {ticker}\n수량: {qty}주 / 가격: ${price}\n🎯 익절: ${tp_price} / 🛑 손절: ${sl_price}"
        else:
            msg = f"❌ [주문실패] {ticker}: {response.text}"
        
        print(msg)
        requests.post(NTFY_URL, data=msg.encode('utf-8'))
    except Exception as e:
        print(f"에러 발생: {e}")

print("🤖 성민0106님의 다이렉트 자동매매 봇 가동...")
while True:
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} 스캔 중...")
    for ticker in tickers:
        price = get_signal(ticker)
        if price:
            buy_order_direct(ticker, price)
            time.sleep(1)
    time.sleep(300)



        
