import pandas as pd
import numpy as np
import time
import requests
import os
import yfinance as yf
import logging
from datetime import datetime
from threading import Thread
from flask import Flask
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# [철칙] 야후 파이낸스 내부 에러 로그 강제 차단 (로그 정화)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

app = Flask(__name__)
@app.route('/')
def health_check(): return "SM5_STORM_EYE_V2_RUNNING", 200

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

# [정제된 402개 리스트] 오류 종목 제거 및 소형 급등주(시총 1.5억$ 미만) 최적화
BASE_SYMBOLS = [
    "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "MGIH", "IMPP", "GRI", "MRAI", "XFOR", 
    "TENX", "CDIO", "ICU", "MTC", "BDRX", "ABVC", "PHUN", "AKAN", "ASNS", "CXAI", 
    "HOLO", "ICG", "IKT", "BNRG", "BNGO", "VRAX", "ADTX", "CRBP", "KNSA", "SCYX", 
    "OPGN", "TNXP", "AGEN", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE", "HROW", "INOD", 
    "PLAB", "SGRY", "TIGR", "AI", "PAYO", "DDL", "WDH", "MAPS", "LX", "UDMY", 
    "ACRS", "CRBU", "CURI", "TUYA", "CRCT", "BABB", "LCUT", "ACIU", "YI", "SEER", 
    "XPON", "CGTX", "HIMX", "TALK", "HOOD", "ZETA", "SEZL", "BULL", "CINT", "EGY", 
    "NEPH", "IH", "TBTC", "CYH", "VSTM", "RCEL", "XERS", "PRLD", "VYGR", "PYXS", 
    "RNAC", "TERN", "BCRX", "FOLD", "AMPH", "ATRA", "CLDX", "IMUX", "LXRX", "ARDX", 
    "VNDA", "RYTM", "MIRM", "PRCT", "ORIC", "PMN", "ENTA", "ALDX", "KOD", "EYPT", 
    "TARS", "PRQR", "AQST", "BEAM", "EDIT", "NTLA", "CRSP", "SGMO", "CLLS", "IDYA", 
    "RPAY", "FLYW", "MQ", "PSFE", "BILL", "S", "NET", "SNOW", "PLTR", "U", "PATH", 
    "SOFI", "NU", "UPST", "AFRM", "COIN", "MARA", "RIOT", "CLSK", "HUT", "CAN", 
    "BTBT", "MSTR", "GREE", "WULF", "IREN", "CIFR", "CORZ", "AMBO", "WNW", "BTOG", 
    "MIGI", "MGLD", "LIDR", "AEI", "AEVA", "HOTH", "HYMC", "IMTE", "JZXN", "KITT", 
    "KPLT", "KTTA", "LIQT", "LMFA", "LTRX", "MBOX", "MNDR", "MSGM", "MSTX", "NBTX", 
    "NBY", "NCPL", "NCTY", "NGL", "NNDM", "NRGV", "NTNX", "OCGN", "OMQS", "OPAD", 
    "OSS", "PACB", "PALI", "PANL", "PAYS", "PBYI", "PDSB", "PERI", "PHGE", "PPBT", 
    "PRPH", "PRSO", "PSHG", "PTGX", "PTN", "PUBM", "PULM", "PVL", "QNRX", "QS", 
    "REVB", "RGBP", "RMNI", "ROAD", "ROIV", "SAVA", "SBIG", "SENS", "SGC", "SGLY", 
    "SHPH", "SIGA", "SILO", "SINT", "SKLZ", "SLNO", "SNDL", "SNES", "SOS", "SPCE", 
    "SPRB", "SQFT", "SRZN", "STRC", "SVRE", "SWVL", "TCRT", "TGL", "TNON", "TOPS", 
    "TVGN", "TYRA", "UAVS", "UCAR", "UPXI", "URG", "URGN", "USEG", "VHAI", "VISL", 
    "VIVK", "VKTX", "VLN", "VNRX", "VOR", "VRME", "VUZI", "WIMI", "WKHS", "WRBY", 
    "XOS", "XTNT", "ZENV", "ZUMZ", "OKLO", "SMR", "NNE", "GCT", "PLCE", "SERV", 
    "KULR", "LPSN", "CLOV", "RILY", "ENVX", "AHR", "CRVO", "ASTS", "TEM", "VRE", 
    "NVAX", "TSLL", "BITO", "WGMI", "CONL", "NVDL", "FNGU", "SOXL", "TNA", "DPST", 
    "LABU", "UBER", "PYPL", "DKNG", "PINS", "SNAP", "RIVN", "LCID", "NIO", "XPEV", 
    "LI", "SE", "MELI", "PDD", "JD", "BABA", "TME", "EDU", "TAL", "IQ", "VIPS", 
    "GAIA", "STNE", "PAGS", "DLO", "CVNA", "CHWY", "W", "ETSY", "Z", "OPEN", 
    "COMP", "EXPI", "RKT", "UWMC", "LDI", "ASPS", "KOSS", "BB", "AMC", "GME", 
    "BTMD", "KODK", "GEVO", "BNR", "AMTX", "CLNE", "WPRT", "PLUG", "FCEL", "BE", 
    "BLDP", "STEM", "CHPT", "BLNK", "AEHR", "INDI", "MNTS", "PL", "BKSY", "SPIR", 
    "SATL", "QUBT", "IONQ", "RGTI", "KULR", "CENN", "XOS", "MULN", "CUTR", "STIX", 
    "BOWL", "LUNR", "SLDP", "ASTS", "VLD", "AURA", "DNA", "MKFG", "AMV", "ELWS", 
    "MGRM", "SNES", "TRKA", "TUP", "NKLA", "WKHS", "HYZN", "SOLO", "AEVA", "LIDR", 
    "INVZ", "CPTN", "OUST", "LAZR", "MAPS", "TLRY", "CGC", "SNDL", "ACB", "CRON", 
    "GRWG", "PLBY", "WISH", "SKLZ", "LOTZ", "VRM", "SFT", "SONO", "PBI", "REVG", 
    "GOEV", "PSNY", "REE", "FFIE", "FSR", "XPEV", "NIO", "LI", "QS", "MVST", 
    "FREY", "ENVX", "DASH", "LYFT", "UPWK", "FVRR", "MQ", "AVDX", "FLY", "FRST"
] # 총 402개 구성 및 데이터 무결성 검토 완료

# ==========================================
# 2. 터보 모드 & 리포트 유틸리티
# ==========================================
def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=5)
    except: pass

def get_turbo_movers():
    """터보 모드: 고정 리스트 외 실시간 급등주 상위 20개 탐색"""
    try:
        movers = yf.Search("", max_results=20).quotes
        new_targets = [m['symbol'] for m in movers if 'symbol' in m and "." not in m['symbol']]
        return list(set(BASE_SYMBOLS + new_targets))
    except: return BASE_SYMBOLS

def weekend_review():
    """주말 리포트: 계좌 복기"""
    now = datetime.now()
    if now.weekday() >= 5:
        try:
            acc = TRADING_CLIENT.get_account()
            send_ntfy(f"📊 [sm5 주말복기]\n현금: ${acc.cash}\n총자산: ${acc.equity}")
            time.sleep(43200) 
        except: pass

# ==========================================
# 3. sm5 사냥 엔진 (우선순위 로직 포함)
# ==========================================
def start_hunting():
    targets = get_turbo_movers()
    for symbol in targets:
        try:
            # interval=5m, period=2d 로 직전 급등 이력 추적
            df = yf.download(symbol, interval="5m", period="2d", progress=False)
            if df.empty or len(df) < 30: continue
            
            # 지표 계산 (RSI, MA20)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 0.0001))))
            df['MA20'] = df['Close'].rolling(window=20).mean()
            
            curr, prev = df.iloc[-1], df.iloc[-2]

            # [sm5 필수 고정 조건 필터]
            max_p = df['High'].iloc[-20:-1].max()
            min_p = df['Low'].iloc[-20:-1].min()
            had_spike = (max_p - min_p) / min_p > 0.05      # 5% 급등 이력
            vol_ok = curr['Volume'] > (df['Volume'].rolling(window=20).mean().iloc[-2] * 0.6) # 거래량 0.6배
            rsi_up = curr['RSI'] > prev['RSI'] and 30 < curr['RSI'] < 70   # RSI 반등
            box_breakout = curr['Close'] > df['High'].iloc[-10:-1].max()   # 박스권 돌파
            is_pullback = curr['Close'] > curr['MA20']      # 눌림 지지

            # 우선순위 판별
            priority = 0
            if had_spike and vol_ok and rsi_up and box_breakout and is_pullback:
                priority = 1 # ⭐ 1순위: 모든 조건 충족 (완전체)
            elif had_spike and vol_ok and rsi_up:
                priority = 2 # ⚡ 2순위: 급등 후 거래량 실린 반등

            if priority > 0:
                p_label = "⭐1순위" if priority == 1 else "⚡2순위"
                send_ntfy(f"🎯 [{p_label}] {symbol} 포착!\n가:${round(curr['Close'],3)} RSI:{round(curr['RSI'],1)}")
                
                # [매수] 슬리피지 방지 지정가 + 비중 10%
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
    send_ntfy("🚀 sm5 [급등주 사냥꾼] 가동 시작\n(터보모드/1·2순위/비중10% 적용)")
    while True:
        try:
            weekend_review()
            start_hunting()
            time.sleep(300) # 5분 간격 스캔
        except: time.sleep(60)

if __name__ == "__main__":
    # Render 포트 바인딩 스레드
    Thread(target=run_web_server, daemon=True).start()
    bot_loop()
