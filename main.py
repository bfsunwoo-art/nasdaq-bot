import sys
import functools
print = functools.partial(print, flush=True)

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import pytz
import threading
import random
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. 설정 (성민0106님 정보)
# ==========================================
ALPACA_API_KEY = 'PKHQEN22KBWB2HSXRGMPWQ3QYL'
ALPACA_SECRET_KEY = 'ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i'
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

# 성민0106 고정 402개 리스트
fixed_tickers = ["TTOO", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "TCBP", "MGIH", "WISA", "IMPP", "GRI", "MRAI", "XFOR", "TENX",
                 "MGRM", "NVOS", "CDIO", "ICU", "MTC", "BDRX", "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "CYTO", "HOLO",
                 "ICG", "IKT", "BNRG", "AITX", "BCEL", "BNGO", "VRAX", "ADTX", "APDN", "TRVN", "CRBP", "KNSA", "SCYX", "OPGN",
                 "TNXP", "AGEN", "SELB", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE", "HROW", "INOD", "PLAB", "SGRY", "TIGR", "AI",
                 "PAYO", "DDL", "WDH", "MAPS", "LX", "UDMY", "ACRS", "CRBU", "CURI", "TUYA", "CRCT", "BABB", "LCUT", "ACIU", "YI",
                 "SEER", "XPON", "CGTX", "HIMX", "IVP", "TALK", "HOOD", "ZETA", "SEZL", "BULL", "CINT", "EGY", "NEPH", "IH", "TBTC",
                 "CYH", "VSTM", "ADAP", "KRON", "RCEL", "MRSN", "XERS", "PRLD", "APLT", "VYGR", "PYXS", "RNAC", "OCUP", "TERN", "BCRX",
                 "FOLD", "AMPH", "ATRA", "CLDX", "IMUX", "CNTG", "LXRX", "ARDX", "VNDA", "SCPH", "PRVB", "ETNB", "ZEAL", "RYTM", "MIRM",
                 "PRCT", "ORIC", "PMN", "ENTA", "ALDX", "KOD", "EYPT", "TARS", "PRQR", "AQST", "VERV", "BEAM", "EDIT", "NTLA", "CRSP",
                 "SGMO", "CLLS", "BLUE", "IDYA", "RPAY", "FLYW", "MQ", "PSFE", "AVDX", "BILL", "BIGC", "SHOP", "S", "NET", "SNOW",
                 "PLTR", "U", "PATH", "C3AI", "SOFI", "NU", "UPST", "AFRM", "COIN", "MARA", "RIOT", "CLSK", "HUT", "CAN", "BTBT",
                 "MSTR", "GREE", "SDIG", "WULF", "IREN", "CIFR", "CORZ", "TERW", "LPTV", "AMBO", "WNW", "BRLI", "BTOG", "MIGI",
                 "MGLD", "LIDR", "AEI", "AERC", "AEVA", "AGBA", "AGRI", "HOTH", "HYMC", "IDEX", "IMTE", "INPX", "ISIG", "ITOS",
                 "JZXN", "KBNT", "KITT", "KPLT", "KSPN", "KTTA", "LIQT", "LMFA", "LOKP", "LSDI", "LTRX", "LYT", "MARK", "MBOX",
                 "METX", "MMV", "MNDR", "MSGM", "MSTX", "MULN", "MYMD", "NAOV", "NBTX", "NBY", "NCPL", "NCTY", "NEPT", "NETE",
                 "NEXI", "NGL", "NINE", "NKLA", "NNDM", "NOBD", "NRBO", "NRGV", "NSAT", "NTEK", "NTNX", "NTP", "NUZE", "NXTP",
                 "OCGN", "OEG", "OIIM", "OMQS", "ONCS", "ONTX", "OPAD", "OSS", "OTRK", "PACB", "PALI", "PANL", "PAYS", "PBTS",
                 "PBYI", "PDSB", "PERI", "PHGE", "PIRS", "POAI", "PPBT", "PRPH", "PRSO", "PSHG", "PSTI", "PTGX", "PTN", "PUBM",
                 "PULM", "PVL", "PWFL", "QNRX", "QS", "REVB", "RGBP", "RKLY", "RMED", "RMNI", "RNER", "RNN", "ROAD", "ROIV",
                 "SAVA", "SBIG", "SBNY", "SDC", "SEEL", "SENS", "SESN", "SFT", "SGBX", "SGC", "SGFY", "SGLY", "SHPH", "SIEN",
                 "SIGA", "SILO", "SINT", "SISI", "SKLZ", "SLGG", "SLNO", "SNAX", "SNDL", "SNES", "SNMP", "SONN", "SOS", "SPCE",
                 "SPI", "SPRB", "SQFT", "SRZN", "STAF", "STRC", "SUNW", "SVRE", "SWVL", "SYRS", "TCRT", "TGC", "TGL", "TMPO",
                 "TNON", "TNXP", "TOPS", "TRKA", "TUP", "TVGN", "TYRA", "UAVS", "UCAR", "UPXI", "URG", "URGN", "USEG", "VGFC",
                 "VHAI", "VIRI", "VISL", "VIVK", "VKTX", "VLD", "VLN", "VNRX", "VOR", "VRME", "VRPX", "VUZI", "WIMI", "WKHS",
                 "WLGS", "WRBY", "WTER", "XELA", "XOS", "XSPA", "XTNT", "YELL", "YGMZ", "ZAPP", "ZENV", "ZEV", "ZOM", "ZUMZ"]

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=5)
    except: pass

# --- [신규] Self-Ping: 10분마다 자신을 깨움 ---
def keep_alive():
    while True:
        try:
            # 로컬 서버에 접속하여 Render가 서버를 재우지 못하게 함
            requests.get("http://localhost:10000", timeout=10)
        except: pass
        time.sleep(600)
threading.Thread(target=keep_alive, daemon=True).start()

def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"sm4 Active")
        def log_message(self, format, *args): return 
    HTTPServer(('0.0.0.0', 10000), Handler).serve_forever()
threading.Thread(target=run_dummy_server, daemon=True).start()

def get_dynamic_tickers():
    try:
        headers = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}
        res = requests.get(f"{ALPACA_BASE_URL}/v2/assets?status=active", headers=headers, timeout=10)
        if res.status_code == 200:
            pool = [a['symbol'] for a in res.json() if a['tradable'] and a['exchange'] in ['NASDAQ', 'NYSE']]
            return random.sample(pool, min(len(pool), 300))
    except: return []
    return []

def buy_order_sm4(ticker, price, stop_loss, strategy_name):
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
        msg = f"🚀 [{strategy_name}] {ticker}\n매수: ${price}\n손절: ${stop_loss}"
        send_ntfy(msg)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    except: pass

def analyze_and_trade(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False, show_errors=False, timeout=8)
        if df.empty or len(df) < 12: return
        
        curr_p = float(df['Close'].iloc[-1])
        curr_v = df['Volume'].iloc[-1]
        avg_v = df['Volume'].iloc[-7:-1].mean()

        # 1. 눌림목 전략 (20% 기준 유지)
        for i in range(-6, -1):
            change = (df['Close'].iloc[i] - df['Open'].iloc[i]) / df['Open'].iloc[i]
            if change >= 0.20:
                support_p = float(df['Low'].iloc[i + 1])
                if (support_p * 0.97) <= curr_p <= (support_p * 1.03):
                    buy_order_sm4(ticker, curr_p, support_p, "🔥sm4-눌림")
                    return

        # 2. [미세조정] RSI/VWAP 전략 (조건 완화로 포착 확률 증가)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        rsi = float(df['RSI'].iloc[-1])
        # RSI 28 이상 + 소폭 상승 시에도 인정, 거래량 배수 1.1배로 완화
        if rsi > 28 and rsi > float(df['RSI'].iloc[-2]):
            if curr_p > (float(df['VWAP'].iloc[-1]) * 0.998) and curr_v > (avg_v * 1.1):
                buy_order_sm4(ticker, curr_p, curr_p * 0.97, "📈sm4-RSI")
    except: pass

if __name__ == "__main__":
    KST = pytz.timezone('Asia/Seoul')
    last_ping_hour = -1
    send_ntfy("🚨 sm4 무한생존 버전 배포 완료!")

    while True:
        now = datetime.now(KST)
        
        # [신규] 매 시간 정각 생존 알림 (ntfy 전송)
        if now.minute == 0 and now.hour != last_ping_hour:
            send_ntfy(f"✅ sm4 정상 가동 중 (현재 {now.hour}시)")
            last_ping_hour = now.hour

        if 18 <= now.hour or now.hour < 6:
            scan_list = list(set(fixed_tickers + get_dynamic_tickers()))
            print(f"⏰ {now.strftime('%H:%M:%S')} - {len(scan_list)}개 스캔 중...")
            for ticker in scan_list:
                analyze_and_trade(ticker)
                time.sleep(0.1)
            print("✨ 사이클 완료. 12분 대기."); time.sleep(720)
        else:
            time.sleep(1800)
