import sys
import functools
import os
from flask import Flask
from threading import Thread

# 출력 즉시 반영 설정
print = functools.partial(print, flush=True)

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import pytz
import random

# ==========================================
# 1. 설정 및 서버 엔진 (Render 생존용)
# ==========================================
ALPACA_API_KEY = 'PKHQEN22KBWB2HSXRGMPWQ3QYL'
ALPACA_SECRET_KEY = 'ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i'
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

# Flask 서버 설정
app = Flask('')

@app.route('/')
def home():
    # UptimeRobot이 접속했을 때 명확한 응답을 주어 서버 동결 방지
    return "SM4-FINAL SERVER IS ONLINE"

def run_web_server():
    # Render의 포트 환경변수를 사용 (기본 10000)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [성민0106님 고정 종목 리스트 402개] ---
fixed_tickers = ["TTOO", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "TCBP", "MGIH", "WISA", "IMPP", "GRI", "MRAI", "XFOR", "TENX", "MGRM", "NVOS", "CDIO", "ICU", "MTC", "BDRX", "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "CYTO", "HOLO", "ICG", "IKT", "BNRG", "AITX", "BCEL", "BNGO", "VRAX", "ADTX", "APDN", "TRVN", "CRBP", "KNSA", "SCYX", "OPGN", "TNXP", "AGEN", "SELB", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE", "HROW", "INOD", "PLAB", "SGRY", "TIGR", "AI", "PAYO", "DDL", "WDH", "MAPS", "LX", "UDMY", "ACRS", "CRBU", "CURI", "TUYA", "CRCT", "BABB", "LCUT", "ACIU", "YI", "SEER", "XPON", "CGTX", "HIMX", "IVP", "TALK", "HOOD", "ZETA", "SEZL", "BULL", "CINT", "EGY", "NEPH", "IH", "TBTC", "CYH", "VSTM", "ADAP", "KRON", "RCEL", "MRSN", "XERS", "PRLD", "APLT", "VYGR", "PYXS", "RNAC", "OCUP", "TERN", "BCRX", "FOLD", "AMPH", "ATRA", "CLDX", "IMUX", "CNTG", "LXRX", "ARDX", "VNDA", "SCPH", "PRVB", "ETNB", "ZEAL", "RYTM", "MIRM", "PRCT", "ORIC", "PMN", "ENTA", "ALDX", "KOD", "EYPT", "TARS", "PRQR", "AQST", "VERV", "BEAM", "EDIT", "NTLA", "CRSP", "SGMO", "CLLS", "BLUE", "IDYA", "RPAY", "FLYW", "MQ", "PSFE", "AVDX", "BILL", "BIGC", "SHOP", "S", "NET", "SNOW", "PLTR", "U", "PATH", "C3AI", "SOFI", "NU", "UPST", "AFRM", "COIN", "MARA", "RIOT", "CLSK", "HUT", "CAN", "BTBT", "MSTR", "GREE", "SDIG", "WULF", "IREN", "CIFR", "CORZ", "TERW", "LPTV", "AMBO", "WNW", "BRLI", "BTOG", "MIGI", "MGLD", "LIDR", "AEI", "AERC", "AEVA", "AGBA", "AGRI", "HOTH", "HYMC", "IDEX", "IMTE", "INPX", "ISIG", "ITOS", "JZXN", "KBNT", "KITT", "KPLT", "KSPN", "KTTA", "LIQT", "LMFA", "LOKP", "LSDI", "LTRX", "LYT", "MARK", "MBOX", "METX", "MMV", "MNDR", "MSGM", "MSTX", "MULN", "MYMD", "NAOV", "NBTX", "NBY", "NCPL", "NCTY", "NEPT", "NETE", "NEXI", "NGL", "NINE", "NKLA", "NNDM", "NOBD", "NRBO", "NRGV", "NSAT", "NTEK", "NTNX", "NTP", "NUZE", "NXTP", "OCGN", "OEG", "OIIM", "OMQS", "ONCS", "ONTX", "OPAD", "OSS", "OTRK", "PACB", "PALI", "PANL", "PAYS", "PBTS", "PBYI", "PDSB", "PERI", "PHGE", "PIRS", "POAI", "PPBT", "PRPH", "PRSO", "PSHG", "PSTI", "PTGX", "PTN", "PUBM", "PULM", "PVL", "PWFL", "QNRX", "QS", "REVB", "RGBP", "RKLY", "RMED", "RMNI", "RNER", "RNN", "ROAD", "ROIV", "SAVA", "SBIG", "SBNY", "SDC", "SEEL", "SENS", "SESN", "SFT", "SGBX", "SGC", "SGFY", "SGLY", "SHPH", "SIEN", "SIGA", "SILO", "SINT", "SISI", "SKLZ", "SLGG", "SLNO", "SNAX", "SNDL", "SNES", "SNMP", "SONN", "SOS", "SPCE", "SPI", "SPRB", "SQFT", "SRZN", "STAF", "STRC", "SUNW", "SVRE", "SWVL", "SYRS", "TCRT", "TGC", "TGL", "TMPO", "TNON", "TNXP", "TOPS", "TRKA", "TUP", "TVGN", "TYRA", "UAVS", "UCAR", "UPXI", "URG", "URGN", "USEG", "VGFC", "VHAI", "VIRI", "VISL", "VIVK", "VKTX", "VKTX", "VLD", "VLN", "VNRX", "VOR", "VRME", "VRPX", "VUZI", "WIMI", "WKHS", "WLGS", "WRBY", "WTER", "XELA", "XOS", "XSPA", "XTNT", "YELL", "YGMZ", "ZAPP", "ZENV", "ZEV", "ZOM", "ZUMZ"]

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=5)
    except: pass

def get_market_shield():
    try:
        idx_data = yf.download(["QQQ", "IWM"], period="2d", interval="1d", progress=False, show_errors=False)
        returns = (idx_data['Close'].iloc[-1] - idx_data['Close'].iloc[-2]) / idx_data['Close'].iloc[-2]
        avg_ret = returns.mean()
        return (avg_ret <= -0.012), avg_ret
    except: return False, 0

def get_dynamic_tickers():
    try:
        headers = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}
        res = requests.get(f"{ALPACA_BASE_URL}/v2/assets?status=active", headers=headers, timeout=10)
        if res.status_code == 200:
            pool = [a['symbol'] for a in res.json() if a['tradable'] and a['exchange'] in ['NASDAQ', 'NYSE']]
            return random.sample(pool, min(len(pool), 300))
    except: return []

def buy_order(ticker, price, stop_loss, strategy_name):
    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}
    qty = max(1, int(100 / price))
    data = {
        "symbol": ticker, "qty": str(qty), "side": "buy", "type": "market",
        "time_in_force": "gtc", "order_class": "bracket",
        "take_profit": {"limit_price": str(round(price * 1.07, 2))},
        "stop_loss": {"stop_price": str(round(stop_loss, 2))}
    }
    try:
        res = requests.post(url, json=data, headers=headers, timeout=10)
        send_ntfy(f"🚀 [{strategy_name}] {ticker}\n매수: ${price}\n손절: ${stop_loss}")
    except: pass

def analyze_and_trade(ticker, shield_active):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False, show_errors=False, timeout=8)
        if df.empty or len(df) < 12: return
        
        curr_p = float(df['Close'].iloc[-1])
        curr_v = df['Volume'].iloc[-1]
        avg_v = df['Volume'].iloc[-7:-1].mean()

        # 1. 눌림목 전략
        for i in range(-6, -1):
            change = (df['Close'].iloc[i] - df['Open'].iloc[i]) / df['Open'].iloc[i]
            if change >= 0.20:
                support_p = float(df['Low'].iloc[i + 1])
                if (support_p * 0.97) <= curr_p <= (support_p * 1.03):
                    if shield_active:
                        send_ntfy(f"⚠️ 폭풍의 눈 포착: {ticker} (지수급락 매수중지)")
                    else:
                        buy_order(ticker, curr_p, support_p, "🔥눌림목")
                    return

        # 2. RSI/VWAP 전략
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        rsi = float(df['RSI'].iloc[-1])
        if rsi > 28 and rsi > float(df['RSI'].iloc[-2]):
            if curr_p > (float(df['VWAP'].iloc[-1]) * 0.998) and curr_v > (avg_v * 1.1):
                if shield_active:
                    send_ntfy(f"⚠️ 폭풍의 눈 포착: {ticker} (지수급락 매수중지)")
                else:
                    buy_order(ticker, curr_p, curr_p * 0.97, "📈RSI반등")
    except: pass

def weekend_review():
    report = "📊 [sm4-Final 주간 데이터 복기 리포트]\n"
    report += "---------------------------------\n"
    test_list = random.sample(fixed_tickers, 30)
    for ticker in test_list:
        try:
            # 주간 변동성 분석 (5일치 데이터)
            df = yf.download(ticker, period="5d", interval="60m", progress=False, show_errors=False)
            if df.empty: continue
            max_r = (df['High'].max() - df['Low'].min()) / df['Low'].min()
            
            # 목표 변동성(약 20%) 발생 여부 체크
            if 0.15 <= max_r <= 0.25:
                report += f"📍 {ticker}: 변동성 {max_r*100:.1f}% (타겟범위)\n"
            elif max_r > 0.25:
                report += f"🔥 {ticker}: 변동성 {max_r*100:.1f}% (폭발적)\n"
        except: continue
    report += "---------------------------------\n"
    report += "✅ 데이터 기반 복리 전환 기초 자료 수집 완료."
    send_ntfy(report)

# ==========================================
# 2. 실행 메인 루프
# ==========================================
if __name__ == "__main__":
    # Render 헬스체크용 Flask 서버 실행
    Thread(target=run_web_server, daemon=True).start()
    
    KST = pytz.timezone('Asia/Seoul')
    # 현재 시간(Hour)을 초기 저장
    last_ping_hour = datetime.now(KST).hour
    send_ntfy("🚨 sm4-Final 통합 버전 배포 완료 (알람보정 적용)")

    while True:
        now = datetime.now(KST)
        
        # [수정된 생존 신고] 정각을 놓쳐도 시간(Hour)이 바뀌면 즉시 발송
        if now.hour != last_ping_hour:
            send_ntfy(f"✅ sm4 가동중 (현재 {now.hour}시)")
            last_ping_hour = now.hour

        # [주말 업무] 토요일 오전 10시 (리포트 발송)
        if now.weekday() == 5 and now.hour == 10 and 0 <= now.minute < 15:
            weekend_review()
            time.sleep(1000) # 중복 실행 방지

        # [평일 본장 스캔] 한국시간 18시 ~ 익일 06시
        if 18 <= now.hour or now.hour < 6:
            shield_active, mkt_val = get_market_shield()
            dynamic = get_dynamic_tickers()
            scan_list = list(set(fixed_tickers + (dynamic if dynamic else [])))
            for ticker in scan_list:
                analyze_and_trade(ticker, shield_active)
                time.sleep(0.1)
            time.sleep(720) # 스캔 후 휴식 (이 기간 중 시간이 바뀌어도 위 로직이 잡아냄)
        else:
            # 장외 시간엔 대기
            time.sleep(1800)
