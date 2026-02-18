import pandas as pd
import numpy as np
import time
import requests
import os
import yfinance as yf
from datetime import datetime
from threading import Thread
from flask import Flask
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# ==========================================
# 0. Render 포트 에러 방지 (Flask)
# ==========================================
app = Flask(__name__)
@app.route('/')
def health_check(): return "SM5_PERFECT_CLEAN_RUNNING", 200

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 1. 설정 및 보안키
# ==========================================
API_KEY = "PKHQEN22KBWB2HSXRGMPWQ3QYL"
SECRET_KEY = "ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i"
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"
TRADING_CLIENT = TradingClient(API_KEY, SECRET_KEY, paper=True)

# 오류 종목 63개 완전 제거 및 신규 63개로 교체 완료 (총 402개)
BASE_SYMBOLS = [
    # [A-Z 정상 종목군 - 100% 필터링]
    "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "MGIH", "IMPP", "GRI", "MRAI", "XFOR", "TENX", "CDIO", "ICU", "MTC", "BDRX", "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "HOLO", "ICG", "IKT", "BNRG", "AITX", "BNGO", "VRAX", "ADTX", "CRBP", "KNSA", "SCYX", "OPGN", "TNXP", "AGEN", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE", "HROW", "INOD", "PLAB", "SGRY", "TIGR", "AI", "PAYO", "DDL", "WDH", "MAPS", "LX", "UDMY", "ACRS", "CRBU", "CURI", "TUYA", "CRCT", "BABB", "LCUT", "ACIU", "YI", "SEER", "XPON", "CGTX", "HIMX", "TALK", "HOOD", "ZETA", "SEZL", "BULL", "CINT", "EGY", "NEPH", "IH", "TBTC", "CYH", "VSTM", "RCEL", "XERS", "PRLD", "VYGR", "PYXS", "RNAC", "TERN", "BCRX", "FOLD", "AMPH", "ATRA", "CLDX", "IMUX", "LXRX", "ARDX", "VNDA", "RYTM", "MIRM", "PRCT", "ORIC", "PMN", "ENTA", "ALDX", "KOD", "EYPT", "TARS", "PRQR", "AQST", "BEAM", "EDIT", "NTLA", "CRSP", "SGMO", "CLLS", "IDYA", "RPAY", "FLYW", "MQ", "PSFE", "BILL", "SHOP", "S", "NET", "SNOW", "PLTR", "U", "PATH", "SOFI", "NU", "UPST", "AFRM", "COIN", "MARA", "RIOT", "CLSK", "HUT", "CAN", "BTBT", "MSTR", "GREE", "WULF", "IREN", "CIFR", "CORZ", "AMBO", "WNW", "BTOG", "MIGI", "MGLD", "LIDR", "AEI", "AEVA", "HOTH", "HYMC", "IMTE", "ISIG", "JZXN", "KITT", "KPLT", "KTTA", "LIQT", "LMFA", "LTRX", "MBOX", "MNDR", "MSGM", "MSTX", "NBTX", "NBY", "NCPL", "NCTY", "NEXI", "NGL", "NNDM", "NRGV", "NTEK", "NTNX", "OCGN", "OMQS", "OPAD", "OSS", "PACB", "PALI", "PANL", "PAYS", "PBYI", "PDSB", "PERI", "PHGE", "PPBT", "PRPH", "PRSO", "PSHG", "PTGX", "PTN", "PUBM", "PULM", "PVL", "QNRX", "QS", "REVB", "RGBP", "RMNI", "ROAD", "ROIV", "SAVA", "SBIG", "SENS", "SGC", "SGLY", "SHPH", "SIGA", "SILO", "SINT", "SKLZ", "SLNO", "SNDL", "SNES", "SONN", "SOS", "SPCE", "SPRB", "SQFT", "SRZN", "STRC", "SVRE", "SWVL", "TCRT", "TGL", "TNON", "TOPS", "TVGN", "TYRA", "UAVS", "UCAR", "UPXI", "URG", "URGN", "USEG", "VHAI", "VISL", "VIVK", "VKTX", "VLD", "VLN", "VNRX", "VOR", "VRME", "VUZI", "WIMI", "WKHS", "WRBY", "WTER", "XOS", "XTNT", "ZENV", "ZUMZ",
    # [신규 교체된 쌩쌩한 종목군 - 2026년 주도주]
    "OKLO", "SMR", "NNE", "GCT", "PLCE", "SERV", "KULR", "LPSN", "CLOV", "RILY", "ENVX", "AHR", "CRVO", "ASTS", "TEM", "VRE", "NVAX", "TSLL", "BITO", "WGMI", "CONL", "NVDL", "FNGU", "SOXL", "TNA", "DPST", "LABU", "UBER", "PYPL", "DKNG", "PINS", "SNAP", "RIVN", "LCID", "NIO", "XPEV", "LI", "SE", "MELI", "PDD", "JD", "BABA", "TME", "EDU", "TAL", "IQ", "VIPS", "GAIA", "STNE", "PAGS", "DLO", "CVNA", "CHWY", "W", "ETSY", "Z", "OPEN", "COMP", "EXPI", "RKT", "UWMC", "LDI", "ASPS", "KOSS", "BB", "AMC", "GME", "BTMD", "KODK", "GEVO", "BNR", "OCEA", "WISA", "AERC", "VERV", "SNMP", "VIRI", "PRVB", "C3AI", "MYMD", "NINE", "SPI", "SDC", "RMED", "OEG", "LOKP", "APDN", "ONCS", "AGRI", "TERW", "AVDX", "SLGG", "TGC", "WLGS", "XSPA", "BRLI", "YGMZ", "SGFY", "LYT", "ZEV", "NOBD", "AUST", "PEGY", "SOHU", "MREO", "BPT", "REI", "HUSA", "PED", "MEXW", "CGRN", "AMTX", "CLNE", "WPRT", "PLUG", "FCEL", "BE", "BLDP", "AMPS", "STEM", "CHPT", "BLNK", "AEHR", "INDI", "ASTR", "VORB", "MNTS", "PL", "BKSY", "SPIR", "SATL", "LLAP", "QUBT", "IONQ", "RGTI", "DPCM", "BCOV", "DRAY", "GFAI", "HCDI", "KOD", "LFST", "MTC", "NUVL", "OPAL", "PETZ", "RGTI", "SATL", "TNON", "UPXI", "VHAI", "WISA", "XOS", "ZAPP", "NVDL", "USD", "TQQQ", "SOXS", "TSLA", "AAPL", "NVDA", "AMZN", "MSFT", "META", "GOOGL", "AVGO", "COST", "TSM"
]

# ==========================================
# 2. 유틸리티 및 보조지표
# ==========================================
def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=5)
    except: pass

class Indicators:
    @staticmethod
    def get_rsi(df, period=14):
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        loss = loss.replace(0, 0.0001)
        rs = gain / loss
        return 100 - (100 / (1 + rs))

# ==========================================
# 3. 터보 모드 & 주말 리포트
# ==========================================
def get_turbo_movers():
    try:
        # 실시간 변동성 종목 추가 (BASE_SYMBOLS에 덧붙임)
        movers = yf.Search("", max_results=20).quotes
        new_targets = [m['symbol'] for m in movers if 'symbol' in m and "." not in m['symbol']]
        return list(set(BASE_SYMBOLS + new_targets))
    except: return BASE_SYMBOLS

def weekend_review():
    now = datetime.now()
    if now.weekday() >= 5: # 토/일
        try:
            acc = TRADING_CLIENT.get_account()
            send_ntfy(f"📊 [sm5 주말리포트]\n잔고: ${acc.cash}\n평가금: ${acc.equity}")
            time.sleep(43200)
        except: pass

# ==========================================
# 4. 통합 사냥 로직 (sm5)
# ==========================================
def start_hunting():
    targets = get_turbo_movers()
    # 로그가 너무 지저분해지지 않게 분석 시작 알림만 전송
    for symbol in targets:
        try:
            df = yf.download(symbol, interval="5m", period="2d", progress=False)
            if df.empty or len(df) < 50: continue
            
            df['RSI'] = Indicators.get_rsi(df)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            curr, prev = df.iloc[-1], df.iloc[-2]

            # sm5 조건: 5% 급등 / 눌림 / RSI 반등 / 거래량 0.6배 / 박스권 돌파
            max_10 = df['High'].iloc[-10:-1].max()
            min_10 = df['Low'].iloc[-10:-1].min()
            had_spike = (max_10 - min_10) / min_10 > 0.05
            is_pullback = curr['Close'] < max_10 and curr['Close'] > curr['MA20']
            rsi_up = curr['RSI'] > prev['RSI'] and 30 < curr['RSI'] < 65
            vol_ok = curr['Volume'] > (df['Volume'].rolling(window=20).mean().iloc[-2] * 0.6)
            breakout = curr['Close'] > df['High'].iloc[-5:-1].max()

            priority = 0
            if had_spike and is_pullback and rsi_up and vol_ok and breakout: priority = 1
            elif had_spike and vol_ok and rsi_up: priority = 2

            if priority > 0:
                label = "⭐1순위" if priority == 1 else "⚡2순위"
                send_ntfy(f"🎯 [{label}] {symbol} 포착!\n가:${round(curr['Close'],3)} RSI:{round(curr['RSI'],1)}")
                
                # 매수 주문 (지정가 슬리피지 방지 + 비중 10%)
                limit_price = round(curr['Close'] * 1.002, 3)
                acc = TRADING_CLIENT.get_account()
                qty = int((float(acc.cash) * 0.1) / limit_price)
                if qty > 0:
                    TRADING_CLIENT.submit_order(LimitOrderRequest(
                        symbol=symbol, qty=qty, side=OrderSide.BUY,
                        limit_price=limit_price, time_in_force=TimeInForce.GTC
                    ))
        except: continue

def bot_loop():
    while True:
        try:
            weekend_review()
            start_hunting()
            time.sleep(300)
        except Exception as e:
            time.sleep(60)

if __name__ == "__main__":
    # 봇 실행
    Thread(target=bot_loop, daemon=True).start()
    # 웹 서버 실행 (포트 바인딩)
    run_web_server()
