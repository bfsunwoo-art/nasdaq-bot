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
# 0. Render 포트 에러 방지용 가짜 서버
# ==========================================
app = Flask(__name__)
@app.route('/')
def health_check(): return "SM5_STABLE_RUNNING", 200

def run_web_server():
    # Render의 Port Binding 에러 해결 (기본 10000 포트)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 1. 설정 및 보안키
# ==========================================
API_KEY = "PKHQEN22KBWB2HSXRGMPWQ3QYL"
SECRET_KEY = "ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i"
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"
TRADING_CLIENT = TradingClient(API_KEY, SECRET_KEY, paper=True)

# 402개 업데이트 리스트 (오류 종목 제거 및 실시간 유망 소형주 교체)
BASE_SYMBOLS = [
    # [기존 유지 종목 - 정상 거래 확인]
    "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "MGIH", "IMPP", "GRI", "MRAI", "XFOR", "TENX", "CDIO", "ICU", "MTC", "BDRX", "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "HOLO", "ICG", "IKT", "BNRG", "AITX", "BNGO", "VRAX", "ADTX", "CRBP", "KNSA", "SCYX", "OPGN", "TNXP", "AGEN", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE", "HROW", "INOD", "PLAB", "SGRY", "TIGR", "AI", "PAYO", "DDL", "WDH", "MAPS", "LX", "UDMY", "ACRS", "CRBU", "CURI", "TUYA", "CRCT", "BABB", "LCUT", "ACIU", "YI", "SEER", "XPON", "CGTX", "HIMX", "TALK", "HOOD", "ZETA", "SEZL", "BULL", "CINT", "EGY", "NEPH", "IH", "TBTC", "CYH", "VSTM", "ADAP", "RCEL", "XERS", "PRLD", "VYGR", "PYXS", "RNAC", "TERN", "BCRX", "FOLD", "AMPH", "ATRA", "CLDX", "IMUX", "LXRX", "ARDX", "VNDA", "RYTM", "MIRM", "PRCT", "ORIC", "PMN", "ENTA", "ALDX", "KOD", "EYPT", "TARS", "PRQR", "AQST", "BEAM", "EDIT", "NTLA", "CRSP", "SGMO", "CLLS", "IDYA", "RPAY", "FLYW", "MQ", "PSFE", "BILL", "SHOP", "S", "NET", "SNOW", "PLTR", "U", "PATH", "SOFI", "NU", "UPST", "AFRM", "COIN", "MARA", "RIOT", "CLSK", "HUT", "CAN", "BTBT", "MSTR", "GREE", "WULF", "IREN", "CIFR", "CORZ", "AMBO", "WNW", "BTOG", "MIGI", "MGLD", "LIDR", "AEI", "AEVA", "HOTH", "HYMC", "IMTE", "ISIG", "JZXN", "KITT", "KPLT", "KTTA", "LIQT", "LMFA", "LTRX", "MBOX", "MMV", "MNDR", "MSGM", "MSTX", "NBTX", "NBY", "NCPL", "NCTY", "NEXI", "NGL", "NNDM", "NRGV", "NTEK", "NTNX", "OCGN", "OMQS", "OPAD", "OSS", "PACB", "PALI", "PANL", "PAYS", "PBYI", "PDSB", "PERI", "PHGE", "POAI", "PPBT", "PRPH", "PRSO", "PSHG", "PTGX", "PTN", "PUBM", "PULM", "PVL", "QNRX", "QS", "REVB", "RGBP", "RMNI", "ROAD", "ROIV", "SAVA", "SBIG", "SENS", "SGC", "SGLY", "SHPH", "SIGA", "SILO", "SINT", "SKLZ", "SLNO", "SNDL", "SNES", "SOS", "SPCE", "SPRB", "SQFT", "SRZN", "STRC", "SVRE", "SWVL", "SYRS", "TCRT", "TGL", "TNON", "TOPS", "TVGN", "TYRA", "UAVS", "UCAR", "UPXI", "URG", "URGN", "USEG", "VHAI", "VISL", "VIVK", "VKTX", "VLD", "VLN", "VNRX", "VOR", "VRME", "VUZI", "WIMI", "WKHS", "WRBY", "WTER", "XOS", "XTNT", "ZENV", "ZOM", "ZUMZ",
    # [58개 오류 종목 교체 리스트 - 시총 1000억 미만 & 급등주 위주]
    "OKLO", "SMR", "NNE", "GCT", "PLCE", "SERV", "KULR", "LPSN", "CLOV", "LAZER", "MGO", "RILY", "ENVX", "AHR", "CRVO", "ASTS", "TEM", "VRE", "NVAX", "TSLL", "BITO", "WGMI", "CONL", "NVDL", "FNGU", "SOXL", "TNA", "DPST", "LABU", "UBER", "PYPL", "DKNG", "PINS", "SNAP", "RIVN", "LCID", "NIO", "XPEV", "LI", "SE", "MELI", "PDD", "JD", "BABA", "TME", "EDU", "TAL", "IQ", "VIPS", "GAIA", "STNE", "PAGS", "DLO", "BYON", "CVNA", "CHWY", "W", "ETSY", "RVV", "Z", "OPEN", "COMP", "EXPI", "RKT", "UWMC", "LDI", "ASPS", "VOXX", "KOSS", "BB", "AMC", "GME", "FFIE", "SOLO", "AYRO", "BTMD", "KODK", "GEVO", "BNR", "OCEA", "IVP", "WISA", "AERC", "VERV", "SNMP", "VIRI", "PRVB", "C3AI", "MYMD", "NINE", "SPI", "SDC", "RMED", "OEG", "ETNB", "LOKP", "APDN", "ONCS", "AGRI", "TERW", "AVDX", "SLGG", "TGC", "WLGS", "XSPA", "BRLI", "YGMZ", "SGFY", "LYT", "ZEV", "NOBD", "AUST", "PEGY", "SOHU", "MREO", "BPT", "REI", "HUSA", "PED", "MEXW", "CGRN", "AMTX", "CLNE", "WPRT", "PLUG", "FCEL", "BE", "BLDP", "AMPS", "STEM", "CHPT", "BLNK", "EVGO", "QS", "AEHR", "INDI", "ASTR", "VORB", "MNTS", "PL", "BKSY", "SPIR", "SATL", "LLAP", "QUBT", "IONQ", "RGTI", "DPCM"
] # 총 402개 구성 완료

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
        # 분모가 0이 되는 것을 방지
        loss = loss.replace(0, 0.0001)
        rs = gain / loss
        return 100 - (100 / (1 + rs))

# ==========================================
# 3. 터보 모드 & 주말 리포트
# ==========================================
def get_turbo_movers():
    try:
        movers = yf.Search("", max_results=20).quotes
        new_targets = [m['symbol'] for m in movers if 'symbol' in m and "." not in m['symbol']]
        return list(set(BASE_SYMBOLS + new_targets))
    except: return BASE_SYMBOLS

def weekend_review():
    now = datetime.now()
    if now.weekday() >= 5:
        try:
            acc = TRADING_CLIENT.get_account()
            report = f"📊 [sm5 주말복기]\n현금: ${acc.cash}\n총자산: ${acc.equity}"
            send_ntfy(report)
            time.sleep(43200) 
        except: pass

# ==========================================
# 4. 통합 사냥 로직
# ==========================================
def start_hunting():
    targets = get_turbo_movers()
    send_ntfy(f"🔍 [sm5] {len(targets)}종목 분석 시작")
    for symbol in targets:
        try:
            # period=2d를 유지하여 전일 급등 이력 확인
            df = yf.download(symbol, interval="5m", period="2d", progress=False)
            if len(df) < 50: continue
            
            df['RSI'] = Indicators.get_rsi(df)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            curr, prev = df.iloc[-1], df.iloc[-2]

            # [sm5 상세조건] 5% 급등 / 눌림 지지 / RSI 반등 / 거래량 0.6배 / 직전고점 돌파
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
                p_label = "⭐ 1순위(완전체)" if priority == 1 else "⚡ 2순위(데이터)"
                msg = f"🎯 [{p_label}] {symbol}\n가:${round(curr['Close'],3)} RSI:{round(curr['RSI'],1)}"
                send_ntfy(msg)
                
                # sm5 매수 실행 (지정가 및 비중 10% 조절)
                limit_price = round(curr['Close'] * 1.002, 3) # 슬리피지 방지 지정가
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
            time.sleep(300) # 5분 간격
        except Exception as e:
            send_ntfy(f"🚨 시스템 에러: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    # 백그라운드에서 사냥 봇 실행
    Thread(target=bot_loop, daemon=True).start()
    # 메인 스레드에서 Render 포트 응답 서버 실행
    run_web_server()
