import os
import sys
import time
import pandas as pd
import pandas_ta as ta
import requests
from pybit.unified_trading import HTTP
from datetime import datetime, timedelta
from flask import Flask  # Render 배포 성공을 위해 추가
import threading      # 가짜 서버를 백그라운드에서 돌리기 위해 추가

# ==========================================
# 1. 설정 및 생존 로직 (stderr 차단)
# ==========================================
sys.stderr = open(os.devnull, 'w') 

API_KEY = "PKHQEN22KBWB2HSXRGMPWQ3QYL"
API_SECRET = "ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i"
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

# --- [추가] Render 포트 바인딩용 가짜 서버 ---
app = Flask(__name__)
@app.route('/')
def health_check():
    return "Sm5 Hunting System is Online", 200

def run_web_server():
    # Render는 PORT 환경변수를 사용하거나 기본 10000번을 사용합니다.
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
# ------------------------------------------

session = HTTP(testnet=True, api_key=API_KEY, api_secret=API_SECRET)

# [핵심 유전자] 시총 1,500억 미만 소형주 402개 리스트
BASE_SYMBOLS = [
    "ROLR", "JTAI", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "MGIH", "IMPP", "CING",
    "SNAL", "MRAI", "BRLS", "HUBC", "AGBA", "ICU", "TPST", "LGVN", "CNEY", "SCPX",
    "TCBP", "KITT", "RVSN", "SERV", "SMFL", "IVP", "WISA", "VHAI", "MGRM", "SPRC",
    "AENT", "AEI", "AEMD", "AEYE", "AEZS", "AFIB", "AIHS", "AIMD", "AITX", "AKAN",
    "AKBA", "AKTX", "ALBT", "ALDX", "ALOT", "ALPP", "ALRN", "ALVOP", "AMBO", "AMST",
    "ANIX", "ANY", "AOMR", "APDN", "APGN", "APLM", "APLT", "APTO", "APVO", "APWC",
    "AQB", "AQMS", "AQST", "ARAV", "ARBB", "ARBE", "ARBK", "ARCT", "ARDS", "ARDX",
    "AREB", "ARGX", "ARL", "ARMP", "ARQT", "ARSN", "ARTL", "ARTW", "ARVN", "ASNS",
    "ASPA", "ASPS", "ASRT", "ASRV", "ASST", "ASTI", "ASTR", "ASTS", "ASXC", "ATAI",
    "ATAK", "ATCG", "ATCP", "ATEC", "ATER", "ATGL", "ATNF", "ATNM", "ATNX", "ATOS",
    "ATPC", "ATRA", "ATRI", "ATRO", "ATXG", "AUBAP", "AUUD", "AVDL", "AVGR", "AVIR",
    "AVRO", "AVTX", "AVXL", "AWIN", "AWRE", "AXLA", "AXNX", "AXTI", "AYRO", "AYTU",
    "AZRE", "AZTR", "BANN", "BCAN", "BCDA", "BCEL", "BCOV", "BCSA", "BDRX", "BETS",
    "BFRI", "BGI", "BGLC", "BGM", "BHAT", "BIAF", "BIG", "BIOC", "BITF", "BKYI",
    "BLBX", "BLIN", "BLNK", "BLPH", "BLRX", "BLTE", "BLUE", "BMRA", "BNGO", "BNRG",
    "BNTC", "BOF", "BOSC", "BOXD", "BPT", "BRDS", "BRIB", "BRQS", "BRSH", "BRTX",
    "BSFC", "BSGM", "BTBD", "BTBT", "BTCS", "BTM", "BTOG", "BTTR", "BTTX", "BTU",
    "BURG", "BXRX", "BYFC", "BYRN", "BYSI", "BZFD", "CAPR", "CARV", "CASI", "CASS",
    "CATX", "CBAS", "CBIO", "CBMG", "CEMI", "CENN", "CENT", "CETY", "CEZA", "CFRX",
    "CGON", "CHNR", "CHRS", "CHSN", "CIDM", "CIFR", "CINC", "CIZN", "CJJD", "CKPT",
    "CLAR", "CLDI", "CLIR", "CLNE", "CLNN", "CLRB", "CLRO", "CLSD", "CLSK", "CLSN",
    "CLVR", "CLXT", "CMAX", "CMND", "CMRA", "CMRX", "CNET", "CNSP", "CNTX", "CNXA",
    "COCP", "CODX", "COGT", "COIN", "COMS", "CPHI", "CPIX", "CPOP", "CPTN", "CPX",
    "CRBP", "CRDL", "CRKN", "CRMD", "CRTD", "CRVO", "CRVS", "CSCW", "CSSEL", "CTIB",
    "CTIC", "CTLP", "CTMX", "CTNT", "CTRM", "CTSO", "CTXR", "CUEN", "CURI", "CVLB",
    "CVV", "CWBR", "CXAI", "CYAD", "CYAN", "CYBN", "CYCC", "CYCN", "CYN", "CYRN",
    "CYTK", "CYTO", "DARE", "DATS", "DBGI", "DCFC", "DCO", "DCTH", "DFFN", "DGHI",
    "DGLY", "DJV", "DLPN", "DMTK", "DNA", "DNMR", "DNUT", "DOMO", "DRMA", "DRRX",
    "DRTS", "DRUG", "DSCR", "DSGN", "DSKE", "DSSI", "DSX", "DTIL", "DTSS", "DVAX",
    "DXF", "DYAI", "DYNT", "DZZX", "EAAS", "EBIZ", "EBLU", "EBON", "ECOR", "EDBL",
    "EDSA", "EDTK", "EEIQ", "EFOI", "EGAN", "EGLX", "EGRX", "EHTH", "EIGI", "EKSO",
    "ELOX", "ELTK", "EMBK", "EMKR", "ENCP", "ENLV", "ENOB", "ENSC", "ENSV", "ENTG",
    "ENTX", "ENVB", "ENZC", "EOLS", "EOSE", "EPAY", "EPIX", "EPRX", "EQ", "EQOS",
    "ERAS", "ERC", "ERYP", "ESEA", "ESGC", "ESPR", "ETTX", "EVFM", "EVGN", "EVGO",
    "EVOK", "EVTV", "EXAI", "EXPR", "EYE", "EYEN", "EYPT", "FAMI", "FATE", "FBIO",
    "FBRX", "FCEL", "FCON", "FCRD", "FDMT", "FDP", "FENC", "FEXD", "FGEN", "FIXX",
    "FKWL", "FLGC", "FLGT", "FLUX", "FLXN", "FMTX", "FNCH", "FNHC", "FNKO", "FORW"
]

TURBO_SYMBOLS = []
LAST_TURBO_SCAN = None
active_positions = {} 
trade_history = [] 

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'))
    except: pass

# ==========================================
# 2. 한국 시간(KST) 및 리포트 로직
# ==========================================
def get_kst_now():
    # Render 서버 시간(UTC)에 9시간을 더해 한국 시간 반환
    return datetime.utcnow() + timedelta(hours=9)

def send_weekend_report():
    kst_now = get_kst_now()
    if kst_now.weekday() == 5 and kst_now.hour == 9 and kst_now.minute == 0:
        if not trade_history:
            msg = "📊 [주말 리포트] 이번 주 거래 내역이 없습니다."
        else:
            df_hist = pd.DataFrame(trade_history)
            win_rate = (df_hist['profit'] > 0).mean() * 100
            total_profit = df_hist['profit'].sum()
            msg = f"📊 [주말 계좌 복기 리포트]\n- 건수: {len(df_hist)}건\n- 승률: {win_rate:.2f}%\n- 수익: {total_profit:.2f}%"
        send_ntfy(msg)
        trade_history.clear()

def check_heartbeat():
    # [수정] 한국 시간(KST) 기준으로 알림 전송
    kst_now = get_kst_now()
    if kst_now.minute == 0:
        send_ntfy(f"📡 [sm5] {kst_now.strftime('%H:%M')} 가동 중 | 포지션: {len(active_positions)}개")

# ==========================================
# 3. 탐색 및 방어막 (본장 30분 대기)
# ==========================================
def update_turbo_movers():
    global TURBO_SYMBOLS, LAST_TURBO_SCAN
    kst_now = get_kst_now()
    if LAST_TURBO_SCAN is None or (kst_now - LAST_TURBO_SCAN).total_seconds() >= 3600:
        try:
            tickers = session.get_tickers(category="spot")
            sorted_tickers = sorted(tickers['result']['list'], key=lambda x: float(x['lastPrice']) / float(x['prevPrice24h']), reverse=True)
            new_list = [t['symbol'].replace("USDT", "") for t in sorted_tickers]
            TURBO_SYMBOLS = [s for s in new_list if s not in BASE_SYMBOLS][:15]
            LAST_TURBO_SCAN = kst_now
            send_ntfy(f"🚀 터보 탐색 완료 (신규 15개 감시)")
        except: pass

def is_market_safe():
    kst_now = get_kst_now()
    if (kst_now.hour == 23 and kst_now.minute >= 30) or (kst_now.hour == 0 and kst_now.minute < 1):
        return False
    return True

# ==========================================
# 4. 사냥 엔진 (개선된 Trailing Stop 반영)
# ==========================================
def manage_position(symbol, curr_price):
    if symbol not in active_positions: return
    pos = active_positions[symbol]
    
    pos['highest_price'] = max(pos.get('highest_price', curr_price), curr_price)
    profit = (curr_price - pos['entry_price']) / pos['entry_price']
    drop_from_top = (pos['highest_price'] - curr_price) / pos['highest_price']
    priority = pos['priority']

    if priority in [1, 2]:
        if profit <= -0.03:
            msg = f"📉 [손절] {symbol} ({priority}순위)\n손실률: {profit*100:.2f}%"
            send_ntfy(msg)
            trade_history.append({'symbol': symbol, 'profit': profit*100})
            del active_positions[symbol]
        elif profit > 0 and drop_from_top >= 0.03:
            msg = f"💰 [추적익절] {symbol} ({priority}순위)\n최종수익: {profit*100:.2f}%\n고점대비하락: {drop_from_top*100:.2f}%"
            send_ntfy(msg)
            trade_history.append({'symbol': symbol, 'profit': profit*100})
            del active_positions[symbol]
    elif priority == 3:
        if profit >= 0.05:
            send_ntfy(f"💰 [3순위 익절] {symbol}\n수익률: {profit*100:.2f}%")
            trade_history.append({'symbol': symbol, 'profit': profit*100})
            del active_positions[symbol]
        elif profit <= -0.03:
            send_ntfy(f"📉 [3순위 손절] {symbol}\n손실률: {profit*100:.2f}%")
            trade_history.append({'symbol': symbol, 'profit': profit*100})
            del active_positions[symbol]

def start_hunting(symbol):
    if symbol in active_positions:
        try:
            candles = session.get_kline(category="spot", symbol=f"{symbol}USDT", interval="5", limit=1)
            manage_position(symbol, float(candles['result']['list'][0][4]))
        except: pass
        return

    try:
        candles = session.get_kline(category="spot", symbol=f"{symbol}USDT", interval="5", limit=50)
        df = pd.DataFrame(candles['result']['list'], columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Turnover'])
        df = df.astype(float).iloc[::-1]
        df['RSI'] = ta.rsi(df['Close'], length=14)
    except: return

    curr, prev = df.iloc[-1], df.iloc[-2]
    vol_avg = df['Volume'].rolling(window=20).mean().iloc[-2]
    
    vol_ok = curr['Volume'] > (vol_avg * 0.6)
    vol_surge = curr['Volume'] > (vol_avg * 1.5)
    had_spike = (df['High'].iloc[-10:].max() / df['Low'].iloc[-10:].min()) > 1.05
    box_breakout = curr['Close'] > df['High'].iloc[-15:-1].max()
    rsi_up = curr['RSI'] > prev['RSI']
    is_supported = curr['Low'] >= df['Low'].iloc[-5:-1].min()

    priority, weight = 0, 0
    if had_spike and vol_ok and rsi_up and box_breakout and is_supported:
        priority, weight = 1, 0.12
    elif had_spike and vol_ok and rsi_up:
        priority, weight = 2, 0.08
    elif vol_surge and curr['RSI'] > 40:
        priority, weight = 3, 0.05

    if priority > 0:
        buy_price = round(curr['Close'] * 1.002, 4)
        active_positions[symbol] = {'entry_price': buy_price, 'highest_price': buy_price, 'priority': priority}
        send_ntfy(f"🎯 [{priority}순위 포착] {symbol}\n진입가: {buy_price}\n비중: {weight*100}%")

# ==========================================
# 5. 메인 루프 (업데이트됨)
# ==========================================
if __name__ == "__main__":
    # 1. 포트 감시용 가짜 서버 스레드 실행 (Render 배포 통과용)
    threading.Thread(target=run_web_server, daemon=True).start()
    
    send_ntfy(f"🚀 sm5-위대한 항로 V3.2 사냥 시작 (KST 적용)")
    
    while True:
        try:
            if not is_market_safe():
                time.sleep(60)
                continue

            check_heartbeat()
            send_weekend_report()
            update_turbo_movers()
            
            scan_list = list(set(BASE_SYMBOLS + TURBO_SYMBOLS))
            for symbol in scan_list:
                start_hunting(symbol)
                time.sleep(0.3)
        except Exception as e:
            time.sleep(10)
