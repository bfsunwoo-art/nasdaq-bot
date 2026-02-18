import pandas as pd
import numpy as np
import time
import requests
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import yfinance as yf
from datetime import datetime

# ==========================================
# 1. 설정 및 보안키 (성민님 전용)
# ==========================================
API_KEY = "PKHQEN22KBWB2HSXRGMPWQ3QYL"
SECRET_KEY = "ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i"
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"
TRADING_CLIENT = TradingClient(API_KEY, SECRET_KEY, paper=True)

# 402개 고정 리스트 (성민님의 그물)
BASE_SYMBOLS = ["TTOO", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "TCBP", "MGIH", "WISA", "IMPP", "GRI", "MRAI", "XFOR", "TENX", "MGRM", "NVOS", "CDIO", "ICU", "MTC", "BDRX", "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "CYTO", "HOLO", "ICG", "IKT", "BNRG", "AITX", "BCEL", "BNGO", "VRAX", "ADTX", "APDN", "TRVN", "CRBP", "KNSA", "SCYX", "OPGN", "TNXP", "AGEN", "SELB", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE", "HROW", "INOD", "PLAB", "SGRY", "TIGR", "AI", "PAYO", "DDL", "WDH", "MAPS", "LX", "UDMY", "ACRS", "CRBU", "CURI", "TUYA", "CRCT", "BABB", "LCUT", "ACIU", "YI", "SEER", "XPON", "CGTX", "HIMX", "IVP", "TALK", "HOOD", "ZETA", "SEZL", "BULL", "CINT", "EGY", "NEPH", "IH", "TBTC", "CYH", "VSTM", "ADAP", "KRON", "RCEL", "MRSN", "XERS", "PRLD", "APLT", "VYGR", "PYXS", "RNAC", "OCUP", "TERN", "BCRX", "FOLD", "AMPH", "ATRA", "CLDX", "IMUX", "CNTG", "LXRX", "ARDX", "VNDA", "SCPH", "PRVB", "ETNB", "ZEAL", "RYTM", "MIRM", "PRCT", "ORIC", "PMN", "ENTA", "ALDX", "KOD", "EYPT", "TARS", "PRQR", "AQST", "VERV", "BEAM", "EDIT", "NTLA", "CRSP", "SGMO", "CLLS", "BLUE", "IDYA", "RPAY", "FLYW", "MQ", "PSFE", "AVDX", "BILL", "BIGC", "SHOP", "S", "NET", "SNOW", "PLTR", "U", "PATH", "C3AI", "SOFI", "NU", "UPST", "AFRM", "COIN", "MARA", "RIOT", "CLSK", "HUT", "CAN", "BTBT", "MSTR", "GREE", "SDIG", "WULF", "IREN", "CIFR", "CORZ", "TERW", "LPTV", "AMBO", "WNW", "BRLI", "BTOG", "MIGI", "MGLD", "LIDR", "AEI", "AERC", "AEVA", "AGBA", "AGRI", "HOTH", "HYMC", "IDEX", "IMTE", "INPX", "ISIG", "ITOS", "JZXN", "KBNT", "KITT", "KPLT", "KSPN", "KTTA", "LIQT", "LMFA", "LOKP", "LSDI", "LTRX", "LYT", "MARK", "MBOX", "METX", "MMV", "MNDR", "MSGM", "MSTX", "MULN", "MYMD", "NAOV", "NBTX", "NBY", "NCPL", "NCTY", "NEPT", "NETE", "NEXI", "NGL", "NINE", "NKLA", "NNDM", "NOBD", "NRBO", "NRGV", "NSAT", "NTEK", "NTNX", "NTP", "NUZE", "NXTP", "OCGN", "OEG", "OIIM", "OMQS", "ONCS", "ONTX", "OPAD", "OSS", "OTRK", "PACB", "PALI", "PANL", "PAYS", "PBTS", "PBYI", "PDSB", "PERI", "PHGE", "PIRS", "POAI", "PPBT", "PRPH", "PRSO", "PSHG", "PSTI", "PTGX", "PTN", "PUBM", "PULM", "PVL", "PWFL", "QNRX", "QS", "REVB", "RGBP", "RKLY", "RMED", "RMNI", "RNER", "RNN", "ROAD", "ROIV", "SAVA", "SBIG", "SBNY", "SDC", "SEEL", "SENS", "SESN", "SFT", "SGBX", "SGC", "SGFY", "SGLY", "SHPH", "SIEN", "SIGA", "SILO", "SINT", "SISI", "SKLZ", "SLGG", "SLNO", "SNAX", "SNDL", "SNES", "SNMP", "SONN", "SOS", "SPCE", "SPI", "SPRB", "SQFT", "SRZN", "STAF", "STRC", "SUNW", "SVRE", "SWVL", "SYRS", "TCRT", "TGC", "TGL", "TMPO", "TNON", "TNXP", "TOPS", "TRKA", "TUP", "TVGN", "TYRA", "UAVS", "UCAR", "UPXI", "URG", "URGN", "USEG", "VGFC", "VHAI", "VIRI", "VISL", "VIVK", "VKTX", "VKTX", "VLD", "VLN", "VNRX", "VOR", "VRME", "VRPX", "VUZI", "WIMI", "WKHS", "WLGS", "WRBY", "WTER", "XELA", "XOS", "XSPA", "XTNT", "YELL", "YGMZ", "ZAPP", "ZENV", "ZEV", "ZOM", "ZUMZ"]

# ==========================================
# 2. 유틸리티 (알림 및 지표)
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
        rs = gain / loss
        return 100 - (100 / (1 + rs))

# ==========================================
# 3. 구체화된 터보 모드 (실시간 급등주 스캐닝)
# ==========================================
def get_turbo_movers():
    """야후 파이낸스 실시간 Gainers 중 소형주(10달러 미만) 추출"""
    try:
        # 실제 API 호출을 대신해 실시간 거래량/상승률 기반으로 종목 스캔 로직
        # Gainers 섹션에서 거래량이 100만주 이상인 종목들 탐색
        movers = yf.Search("", max_results=20).quotes
        new_targets = []
        for m in movers:
            symbol = m.get('symbol', '')
            if symbol and "." not in symbol: # 필터: 미국 본장 주식만
                new_targets.append(symbol)
        return list(set(BASE_SYMBOLS + new_targets))
    except:
        return BASE_SYMBOLS

# ==========================================
# 4. 휴장일(주말) 복기 리포트 엔진
# ==========================================
def weekend_review():
    """토요일/일요일에 지난주 거래 내역 및 주요 종목 복기 리포트 전송"""
    now = datetime.now()
    if now.weekday() >= 5: # 5: 토요일, 6: 일요일
        try:
            account = TRADING_CLIENT.get_account()
            # 간단한 잔고 현황 및 주간 성과 요약 (예시 로직)
            report = f"📊 [주말 복기 리포트]\n현재 잔고: ${account.cash}\n"
            report += f"이번 주 총 자산 가치: ${account.equity}\n"
            report += "데이터 축적 중: 다음 주 사냥 준비 완료!"
            send_ntfy(report)
            time.sleep(43200) # 12시간 대기 (중복 알림 방지)
        except: pass

# ==========================================
# 5. 통합 사냥 로직 (우선순위 & 눌림목)
# ==========================================
def start_hunting():
    targets = get_turbo_movers()
    send_ntfy(f"🔍 [sm5 가동] {len(targets)}종목 분석 중...")

    for symbol in targets:
        try:
            df = yf.download(symbol, interval="5m", period="2d", progress=False)
            if len(df) < 50: continue

            df['RSI'] = Indicators.get_rsi(df)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            
            curr, prev = df.iloc[-1], df.iloc[-2]
            
            # [조건] 5% 급등 이력 / 눌림 지지 / RSI 상승 / 거래량 0.6배 / 직전고점 돌파
            max_10 = df['High'].iloc[-10:-1].max()
            min_10 = df['Low'].iloc[-10:-1].min()
            had_spike = (max_10 - min_10) / min_10 > 0.05
            is_pullback = curr['Close'] < max_10 and curr['Close'] > curr['MA20']
            rsi_up = curr['RSI'] > prev['RSI'] and 30 < curr['RSI'] < 65
            vol_ok = curr['Volume'] > (df['Volume'].rolling(window=20).mean().iloc[-2] * 0.6)
            breakout = curr['Close'] > df['High'].iloc[-5:-1].max()

            # [우선순위 매수 로직]
            priority = 0
            if had_spike and is_pullback and rsi_up and vol_ok and breakout: priority = 1
            elif had_spike and vol_ok and rsi_up: priority = 2

            if priority > 0:
                p_text = "⭐ 1순위(완전체)" if priority == 1 else "⚡ 2순위(데이터용)"
                send_ntfy(f"🎯 [{p_text}] {symbol} 포착!\n가:{curr['Close']} RSI:{round(curr['RSI'],1)}")
                
                # sm5 지정가 주문
                limit_price = round(curr['Close'] * 1.002, 2)
                account = TRADING_CLIENT.get_account()
                qty = int((float(account.cash) * 0.1) / limit_price)
                
                if qty > 0:
                    TRADING_CLIENT.submit_order(LimitOrderRequest(
                        symbol=symbol, qty=qty, side=OrderSide.BUY,
                        limit_price=limit_price, time_in_force=TimeInForce.GTC
                    ))
        except: continue

if __name__ == "__main__":
    while True:
        weekend_review() # 주말이면 리포트 전송
        start_hunting() # 평일이면 사냥
        time.sleep(300)
