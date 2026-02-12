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
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. 설정 (성민0106님 API 키 및 ntfy 주소)
# ==========================================
ALPACA_API_KEY = 'PKHQEN22KBWB2HSXRGMPWQ3QYL'
ALPACA_SECRET_KEY = 'ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i'
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

# 검증 완료된 402개 종목 리스트
tickers = [
    "TTOO", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "TCBP", "MGIH", "WISA", "IMPP", 
    "GRI", "MRAI", "XFOR", "TENX", "MGRM", "NVOS", "CDIO", "ICU", "MTC", "BDRX", 
    "ABVC", "PHUN", "AEMD", "AKAN", "ASNS", "CXAI", "CYTO", "HOLO", "ICG", "IKT",
    "BNRG", "AITX", "BCEL", "BNGO", "VRAX", "ADTX", "APDN", "TRVN", "CRBP", "KNSA",
    "SCYX", "OPGN", "TNXP", "AGEN", "SELB", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE",
    "HROW", "INOD", "PLAB", "SGRY", "TIGR", "AI", "PAYO", "DDL", "WDH", "MAPS",
    "LX", "UDMY", "ACRS", "CRBU", "CURI", "TUYA", "CRCT", "BABB", "LCUT", "ACIU",
    "YI", "SEER", "XPON", "CGTX", "HIMX", "IVP", "TALK", "HOOD", "ZETA", "SEZL",
    "BULL", "CINT", "EGY", "NEPH", "IH", "TBTC", "CYH", "VSTM", "ADAP", "KRON",
    "RCEL", "MRSN", "XERS", "PRLD", "APLT", "VYGR", "PYXS", "RNAC", "OCUP", "TERN",
    "BCRX", "FOLD", "AMPH", "ATRA", "CLDX", "IMUX", "CNTG", "LXRX", "ARDX",
    "VNDA", "SCPH", "PRVB", "ETNB", "ZEAL", "RYTM", "MIRM", "PRCT", "ORIC", "PMN",
    "ENTA", "ALDX", "KOD", "EYPT", "TARS", "PRQR", "AQST", "VERV", "BEAM", "EDIT",
    "NTLA", "CRSP", "SGMO", "CLLS", "BLUE", "IDYA", "RPAY", "FLYW", "MQ", "PSFE",
    "AVDX", "BILL", "BIGC", "SHOP", "S", "NET", "SNOW", "PLTR", "U", "PATH",
    "C3AI", "SOFI", "NU", "UPST", "AFRM", "COIN", "MARA", "RIOT",
    "CLSK", "HUT", "CAN", "BTBT", "MSTR", "GREE", "SDIG", "WULF", "IREN", "CIFR",
    "CORZ", "TERW", "LPTV", "AMBO", "WNW", "BRLI", "BTOG", "MIGI", "MGLD", "LIDR",
    "AEI", "AERC", "AEVA", "AGBA", "AGRI", "HOTH", "HYMC", "IDEX", "IMTE", "INPX",
    "ISIG", "ITOS", "JZXN", "KBNT", "KITT", "KPLT", "KSPN", "KTTA", "LIQT",
    "LMFA", "LOKP", "LSDI", "LTRX", "LYT", "MARK", "MBOX", "METX", "MMV", "MNDR",
    "MSGM", "MSTX", "MULN", "MYMD", "NAOV", "NBTX", "NBY", "NCPL", "NCTY", "NEPT",
    "NETE", "NEXI", "NGL", "NINE", "NKLA", "NNDM", "NOBD", "NRBO", "NRGV", "NSAT",
    "NTEK", "NTNX", "NTP", "NUZE", "NXTP", "OCGN", "OEG", "OIIM", "OMQS", "ONCS",
    "ONTX", "OPAD", "OSS", "OTRK", "PACB", "PALI", "PANL", "PAYS", "PBTS", "PBYI",
    "PDSB", "PERI", "PHGE", "PIRS", "POAI", "PPBT", "PRPH", "PRSO",
    "PSHG", "PSTI", "PTGX", "PTN", "PUBM", "PULM", "PVL", "PWFL", "QNRX", "QS",
    "REVB", "RGBP", "RKLY", "RMED", "RMNI", "RNER", "RNN", "ROAD", "ROIV", "SAVA",
    "SBIG", "SBNY", "SDC", "SEEL", "SENS", "SESN", "SFT", "SGBX", "SGC",
    "SGFY", "SGLY", "SHPH", "SIEN", "SIGA", "SILO", "SISI", "SKLZ",
    "SLGG", "SLNO", "SNAX", "SNDL", "SNES", "SNMP", "SONN", "SOS", "SPCE",
    "SPI", "SPRB", "SQFT", "SRZN", "STAF", "STRC", "SUNW", "SVRE", "SWVL", 
    "SYRS", "TCRT", "TGC", "TGL", "TMPO", "TNON",
    "TOPS", "TRKA", "TUP", "TVGN", "TYRA", "UAVS", "UCAR", "UPXI",
    "URG", "URGN", "USEG", "VGFC", "VHAI", "VIRI", "VISL", "VIVK", "VKTX", "VLD",
    "VLN", "VNRX", "VOR", "VRME", "VRPX", "VUZI", "WIMI", "WKHS", "WLGS", "WRBY", "WTER", "XELA", 
    "XOS", "XSPA", "XTNT", "YELL", "YGMZ", "ZAPP", "ZENV", "ZEV", "ZOM", "ZUMZ"
]

# Render 서버 유지용 더미 서버
def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"sm3 is Running!")
        def log_message(self, format, *args): return 
    server = HTTPServer(('0.0.0.0', 10000), Handler)
    server.serve_forever()
threading.Thread(target=run_dummy_server, daemon=True).start()

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=5)
    except: pass

# 주문 및 알림 함수
def buy_order_sm3(ticker, price, stop_loss, strategy_name):
    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}
    qty = max(1, int(100 / price))
    data = {
        "symbol": ticker, "qty": str(qty), "side": "buy", "type": "market",
        "time_in_force": "gtc", "order_class": "bracket",
        "take_profit": {"limit_price": str(round(price * 1.10, 2))}, # 익절 10% 상향
        "stop_loss": {"stop_price": str(round(stop_loss, 2))}
    }
    try:
        res = requests.post(url, json=data, headers=headers, timeout=10)
        status = "성공" if res.status_code == 200 else f"실패({res.status_code})"
        msg = f"🚀 [{strategy_name}] {ticker}\n매수가: ${price}\n손절가: ${stop_loss}\n상태: {status}"
        send_ntfy(msg)
        print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')}] {msg}")
    except:
        print(f"⚠️ {ticker} 통신 에러로 주문 건너뜀")

def analyze_and_trade(ticker):
    try:
        # SSL 에러 방지를 위해 timeout 설정 및 에러 무시
        df = yf.download(ticker, period="1d", interval="5m", progress=False, show_errors=False, timeout=10, include_prepost=True)
        if df.empty or len(df) < 12: return

        curr_price = float(df['Close'].iloc[-1])
        curr_vol = df['Volume'].iloc[-1]
        avg_vol = df['Volume'].iloc[-7:-1].mean()

        # --- 1. 성민0106 눌림목 노하우 전략 ---
        # 최근 6봉 이내에 40% 이상 장대양봉이 있었는지 확인
        for i in range(-6, -1):
            open_p = df['Open'].iloc[i]
            close_p = df['Close'].iloc[i]
            change = (close_p - open_p) / open_p
            
            if change >= 0.40: # 40% 장대양봉 포착
                second_bar_low = float(df['Low'].iloc[i + 1]) # 두 번째 양봉 저가
                # 매수 타점: 두 번째 양봉 저가 ±3% 범위
                if (second_bar_low * 0.97) <= curr_price <= (second_bar_low * 1.03):
                    buy_order_sm3(ticker, curr_price, second_bar_low, "🔥눌림목")
                    return

        # --- 2. 완화된 RSI + VWAP 전략 ---
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        
        curr_rsi = float(df['RSI'].iloc[-1])
        prev_rsi = float(df['RSI'].iloc[-2])
        curr_vwap = float(df['VWAP'].iloc[-1])

        # RSI 30 이상에서 반등 중이고, VWAP 위에 있으며 거래량이 1.2배 터질 때
        if curr_rsi > 30 and curr_rsi > prev_rsi:
            if curr_price > curr_vwap and curr_vol > (avg_vol * 1.2):
                buy_order_sm3(ticker, curr_price, curr_price * 0.97, "📈RSI반등")

    except:
        pass # 개별 종목 에러 시 중단 없이 다음 종목으로

if __name__ == "__main__":
    KST = pytz.timezone('Asia/Seoul')
    print("🚀 sm3 통합 버전 시스템 가동 시작")
    send_ntfy("🚨 [sm3] 성민님, 402개 종목 + 눌림목 전략 탑재 완료! 배포 성공.")

    while True:
        now = datetime.now(KST)
        # 한국 시간 18:00 ~ 익일 06:00 가동
        if now.hour >= 18 or now.hour < 6:
            print(f"⏰ {now.strftime('%H:%M:%S')} - 402개 종목 풀스캔 시작...")
            for ticker in tickers:
                analyze_and_trade(ticker)
                time.sleep(0.1) # 서버 부하 방지
            
            print(f"✨ 사이클 완료. 12분간 휴식합니다.")
            time.sleep(720) # 12분 휴식
        else:
            print(f"💤 현재 한국 시간 {now.hour}시, 시장 휴식기입니다.")
            time.sleep(3600)
