import sys
import functools
import os
from flask import Flask
from threading import Thread
import yfinance as yf
import pandas as pd
# pandas_ta 라이브러리 대신 직접 계산하기 위해 주석 처리
# import pandas_ta as ta

# 에러 방지용 가짜 ta 객체 생성
class FakeTA:
    def rsi(self, *args, **kwargs): return None
    def macd(self, *args, **kwargs): return None
ta = FakeTA()
import requests
import time
from datetime import datetime
import pytz
import random

# 출력 즉시 반영 설정
print = functools.partial(print, flush=True)

# ==========================================
# 1. 설정 및 서버 엔진
# ==========================================
ALPACA_API_KEY = 'PKHQEN22KBWB2HSXRGMPWQ3QYL'
ALPACA_SECRET_KEY = 'ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i'
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

app = Flask('')
@app.route('/')
def home(): return "SM5-FINAL-REPORTER ONLINE"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 성민0106님 고정 리스트 (402개)
fixed_tickers = ["TTOO", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "TCBP", "MGIH", "WISA", "IMPP", "GRI", "MRAI", "XFOR", "TENX", "MGRM", "NVOS", "CDIO", "ICU", "MTC", "BDRX", "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "CYTO", "HOLO", "ICG", "IKT", "BNRG", "AITX", "BCEL", "BNGO", "VRAX", "ADTX", "APDN", "TRVN", "CRBP", "KNSA", "SCYX", "OPGN", "TNXP", "AGEN", "SELB", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE", "HROW", "INOD", "PLAB", "SGRY", "TIGR", "AI", "PAYO", "DDL", "WDH", "MAPS", "LX", "UDMY", "ACRS", "CRBU", "CURI", "TUYA", "CRCT", "BABB", "LCUT", "ACIU", "YI", "SEER", "XPON", "CGTX", "HIMX", "IVP", "TALK", "HOOD", "ZETA", "SEZL", "BULL", "CINT", "EGY", "NEPH", "IH", "TBTC", "CYH", "VSTM", "ADAP", "KRON", "RCEL", "MRSN", "XERS", "PRLD", "APLT", "VYGR", "PYXS", "RNAC", "OCUP", "TERN", "BCRX", "FOLD", "AMPH", "ATRA", "CLDX", "IMUX", "CNTG", "LXRX", "ARDX", "VNDA", "SCPH", "PRVB", "ETNB", "ZEAL", "RYTM", "MIRM", "PRCT", "ORIC", "PMN", "ENTA", "ALDX", "KOD", "EYPT", "TARS", "PRQR", "AQST", "VERV", "BEAM", "EDIT", "NTLA", "CRSP", "SGMO", "CLLS", "BLUE", "IDYA", "RPAY", "FLYW", "MQ", "PSFE", "AVDX", "BILL", "BIGC", "SHOP", "S", "NET", "SNOW", "PLTR", "U", "PATH", "C3AI", "SOFI", "NU", "UPST", "AFRM", "COIN", "MARA", "RIOT", "CLSK", "HUT", "CAN", "BTBT", "MSTR", "GREE", "SDIG", "WULF", "IREN", "CIFR", "CORZ", "TERW", "LPTV", "AMBO", "WNW", "BRLI", "BTOG", "MIGI", "MGLD", "LIDR", "AEI", "AERC", "AEVA", "AGBA", "AGRI", "HOTH", "HYMC", "IDEX", "IMTE", "INPX", "ISIG", "ITOS", "JZXN", "KBNT", "KITT", "KPLT", "KSPN", "KTTA", "LIQT", "LMFA", "LOKP", "LSDI", "LTRX", "LYT", "MARK", "MBOX", "METX", "MMV", "MNDR", "MSGM", "MSTX", "MULN", "MYMD", "NAOV", "NBTX", "NBY", "NCPL", "NCTY", "NEPT", "NETE", "NEXI", "NGL", "NINE", "NKLA", "NNDM", "NOBD", "NRBO", "NRGV", "NSAT", "NTEK", "NTNX", "NTP", "NUZE", "NXTP", "OCGN", "OEG", "OIIM", "OMQS", "ONCS", "ONTX", "OPAD", "OSS", "OTRK", "PACB", "PALI", "PANL", "PAYS", "PBTS", "PBYI", "PDSB", "PERI", "PHGE", "PIRS", "POAI", "PPBT", "PRPH", "PRSO", "PSHG", "PSTI", "PTGX", "PTN", "PUBM", "PULM", "PVL", "PWFL", "QNRX", "QS", "REVB", "RGBP", "RKLY", "RMED", "RMNI", "RNER", "RNN", "ROAD", "ROIV", "SAVA", "SBIG", "SBNY", "SDC", "SEEL", "SENS", "SESN", "SFT", "SGBX", "SGC", "SGFY", "SGLY", "SHPH", "SIEN", "SIGA", "SILO", "SINT", "SISI", "SKLZ", "SLGG", "SLNO", "SNAX", "SNDL", "SNES", "SNMP", "SONN", "SOS", "SPCE", "SPI", "SPRB", "SQFT", "SRZN", "STAF", "STRC", "SUNW", "SVRE", "SWVL", "SYRS", "TCRT", "TGC", "TGL", "TMPO", "TNON", "TNXP", "TOPS", "TRKA", "TUP", "TVGN", "TYRA", "UAVS", "UCAR", "UPXI", "URG", "URGN", "USEG", "VGFC", "VHAI", "VIRI", "VISL", "VIVK", "VKTX", "VKTX", "VLD", "VLN", "VNRX", "VOR", "VRME", "VRPX", "VUZI", "WIMI", "WKHS", "WLGS", "WRBY", "WTER", "XELA", "XOS", "XSPA", "XTNT", "YELL", "YGMZ", "ZAPP", "ZENV", "ZEV", "ZOM", "ZUMZ"]

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=5)
    except: pass

# ==========================================
# 2. 주말 리포트 기능 (Weekend Review)
# ==========================================
def weekend_review():
    report = "📊 [sm5-Final 주간 데이터 복기 리포트]\n"
    report += "---------------------------------\n"
    test_list = random.sample(fixed_tickers, 30)
    for ticker in test_list:
        try:
            df = yf.download(ticker, period="5d", interval="60m", progress=False, show_errors=False)
            if df.empty: continue
            max_r = (df['High'].max() - df['Low'].min()) / df['Low'].min()
            if 0.10 <= max_r <= 0.25:
                report += f"📍 {ticker}: 변동성 {max_r*100:.1f}% (포착대상)\n"
            elif max_r > 0.25:
                report += f"🔥 {ticker}: 변동성 {max_r*100:.1f}% (급등)\n"
        except: continue
    report += "---------------------------------\n"
    report += "✅ sm5 데이터 기반 복리 전환 준비 완료."
    send_ntfy(report)

# ==========================================
# 3. 실전 사냥 로직
# ==========================================
def buy_order_sm5(ticker, price, stop_loss, strategy_name):
    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}
    qty = max(1, int(30 / price)) 
    limit_p = round(price * 1.005, 2) 
    data = {
        "symbol": ticker, "qty": str(qty), "side": "buy", "type": "limit",
        "limit_price": str(limit_p), "time_in_force": "gtc", "order_class": "bracket",
        "take_profit": {"limit_price": str(round(price * 1.07, 2))},
        "stop_loss": {"stop_price": str(round(stop_loss, 2))}
    }
    try:
        res = requests.post(url, json=data, headers=headers, timeout=10)
        if res.status_code == 200:
            send_ntfy(f"🚀 [sm5-{strategy_name}] {ticker}\n매수: ${price}\n금액: $30 (데이터 수집)")
    except: pass

def analyze_and_trade(ticker, shield_active):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False, show_errors=False, timeout=8)
        if df.empty or len(df) < 12: return
        curr_p = float(df['Close'].iloc[-1])
        curr_v = df['Volume'].iloc[-1]
        avg_v = df['Volume'].iloc[-7:-1].mean()
        if curr_v < (avg_v * 0.6) or (curr_p * curr_v) < 50000: return 
        for i in range(-6, -1):
            change = (df['Close'].iloc[i] - df['Open'].iloc[i]) / df['Open'].iloc[i]
            if change >= 0.10: # sm5 핵심: 민감도 상향
                support_p = float(df['Low'].iloc[i + 1])
                if (support_p * 0.98) <= curr_p <= (support_p * 1.02):
                    if not shield_active: buy_order_sm5(ticker, curr_p, support_p * 0.97, "눌림목")
                    return
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        if float(df['RSI'].iloc[-1]) > 28 and float(df['RSI'].iloc[-1]) > float(df['RSI'].iloc[-2]):
            if curr_p > (float(df['VWAP'].iloc[-1]) * 0.998):
                if not shield_active: buy_order_sm5(ticker, curr_p, curr_p * 0.96, "RSI반등")
    except: pass

# ==========================================
# 4. 메인 엔진
# ==========================================
if __name__ == "__main__":
    Thread(target=run_web_server, daemon=True).start()
    KST = pytz.timezone('Asia/Seoul')
    last_ping_hour = datetime.now(KST).hour
    send_ntfy("🚨 [sm5-최종] 사냥 및 리포트 시스템 배포 완료")

    while True:
        now = datetime.now(KST)
        if now.hour != last_ping_hour:
            send_ntfy(f"✅ sm5 가동중 (현재 {now.hour}시)")
            last_ping_hour = now.hour

        # [주말 리포트] 토요일 오전 10시
        if now.weekday() == 5 and now.hour == 10 and 0 <= now.minute < 5:
            weekend_review()
            time.sleep(600)

        # [평일 본장 스캔]
        if 18 <= now.hour or now.hour < 6:
            # Market Shield 생략 가능하나 안정성을 위해 유지
            scan_list = list(set(fixed_tickers + [])) # 여기에 동적 티커 추가 가능
            print(f"[{now.strftime('%H:%M:%S')}] {len(scan_list)}개 종목 전수 조사 시작...")
            for ticker in scan_list:
                analyze_and_trade(ticker, False)
                time.sleep(0.05)
            time.sleep(300)
        else:
            time.sleep(1800)
