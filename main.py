import os
import sys
import time
import pandas as pd
import pandas_ta as ta
import requests
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
from flask import Flask
import threading

# ==========================================
# 1. 설정 및 자가 진단 (Auth & Trace)
# ==========================================
# 데이터 분석을 위해 로그 개방 (필요 시 주석 해제)
# sys.stderr = open(os.devnull, 'w') 

API_KEY = "PKHQEN22KBWB2HSXRGMPWQ3QYL"
API_SECRET = "ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i"
BASE_URL = "https://paper-api.alpaca.markets"
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

reject_log = []
active_positions = {}
trade_history = []

def auth_test():
    try:
        acc = api.get_account()
        if acc.status == 'ACTIVE':
            msg = f"✅ [Auth Success] 계좌 연결됨\nBuying Power: ${float(acc.buying_power):,.2f}"
            print(msg); send_ntfy(msg)
            return True
    except Exception as e:
        error_msg = f"❌ [Auth Failed] API 권한 확인 필요: {e}"
        print(error_msg); send_ntfy(error_msg)
        return False

# ==========================================
# 2. 핵심 유전자 및 전략 설정
# ==========================================
BASE_SYMBOLS = ["ROLR", "JTAI", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "MGIH", "IMPP", "CING", "SNAL", "MRAI", "BRLS", "HUBC", "AGBA", "ICU", "TPST", "LGVN", "CNEY", "SCPX", "TCBP", "KITT", "RVSN", "SERV", "SMFL", "IVP", "WISA", "VHAI", "MGRM", "SPRC", "AENT", "AEI", "AEMD", "AEYE", "AEZS", "AFIB", "AIHS", "AIMD", "AITX", "AKAN", "AKBA", "AKTX", "ALBT", "ALDX", "ALOT", "ALPP", "ALRN", "ALVOP", "AMBO", "AMST", "ANIX", "ANY", "AOMR", "APDN", "APGN", "APLM", "APLT", "APTO", "APVO", "APWC", "AQB", "AQMS", "AQST", "ARAV", "ARBB", "ARBE", "ARBK", "ARCT", "ARDS", "ARDX", "AREB", "ARGX", "ARL", "ARMP", "ARQT", "ARSN", "ARTL", "ARTW", "ARVN", "ASNS", "ASPA", "ASPS", "ASRT", "ASRV", "ASST", "ASTI", "ASTR", "ASTS", "ASXC", "ATAI", "ATAK", "ATCG", "ATCP", "ATEC", "ATER", "ATGL", "ATNF", "ATNM", "ATNX", "ATOS", "ATPC", "ATRA", "ATRI", "ATRO", "ATXG", "AUBAP", "AUUD", "AVDL", "AVGR", "AVIR", "AVRO", "AVTX", "AVXL", "AWIN", "AWRE", "AXLA", "AXNX", "AXTI", "AYRO", "AYTU", "AZRE", "AZTR", "BANN", "BCAN", "BCDA", "BCEL", "BCOV", "BCSA", "BDRX", "BETS", "BFRI", "BGI", "BGLC", "BGM", "BHAT", "BIAF", "BIG", "BIOC", "BITF", "BKYI", "BLBX", "BLIN", "BLNK", "BLPH", "BLRX", "BLTE", "BLUE", "BMRA", "BNGO", "BNRG", "BNTC", "BOF", "BOSC", "BOXD", "BPT", "BRDS", "BRIB", "BRQS", "BRSH", "BRTX", "BSFC", "BSGM", "BTBD", "BTBT", "BTCS", "BTM", "BTOG", "BTTR", "BTTX", "BTU", "BURG", "BXRX", "BYFC", "BYRN", "BYSI", "BZFD", "CAPR", "CARV", "CASI", "CASS", "CATX", "CBAS", "CBIO", "CBMG", "CEMI", "CENN", "CENT", "CETY", "CEZA", "CFRX", "CGON", "CHNR", "CHRS", "CHSN", "CIDM", "CIFR", "CINC", "CIZN", "CJJD", "CKPT", "CLAR", "CLDI", "CLIR", "CLNE", "CLNN", "CLRB", "CLRO", "CLSD", "CLSK", "CLSN", "CLVR", "CLXT", "CMAX", "CMND", "CMRA", "CMRX", "CNET", "CNSP", "CNTX", "CNXA", "COCP", "CODX", "COGT", "COIN", "COMS", "CPHI", "CPIX", "CPOP", "CPTN", "CPX", "CRBP", "CRDL", "CRKN", "CRMD", "CRTD", "CRVO", "CRVS", "CSCW", "CSSEL", "CTIB", "CTIC", "CTLP", "CTMX", "CTNT", "CTRM", "CTSO", "CTXR", "CUEN", "CURI", "CVLB", "CVV", "CWBR", "CXAI", "CYAD", "CYAN", "CYBN", "CYCC", "CYCN", "CYN", "CYRN", "CYTK", "CYTO", "DARE", "DATS", "DBGI", "DCFC", "DCO", "DCTH", "DFFN", "DGHI", "DGLY", "DJV", "DLPN", "DMTK", "DNA", "DNMR", "DNUT", "DOMO", "DRMA", "DRRX", "DRTS", "DRUG", "DSCR", "DSGN", "DSKE", "DSSI", "DSX", "DTIL", "DTSS", "DVAX", "DXF", "DYAI", "DYNT", "DZZX", "EAAS", "EBIZ", "EBLU", "EBON", "ECOR", "EDBL", "EDSA", "EDTK", "EEIQ", "EFOI", "EGAN", "EGLX", "EGRX", "EHTH", "EIGI", "EKSO", "ELOX", "ELTK", "EMBK", "EMKR", "ENCP", "ENLV", "ENOB", "ENSC", "ENSV", "ENTG", "ENTX", "ENVB", "ENZC", "EOLS", "EOSE", "EPAY", "EPIX", "EPRX", "EQ", "EQOS", "ERAS", "ERC", "ERYP", "ESEA", "ESGC", "ESPR", "ETTX", "EVFM", "EVGN", "EVGO", "EVOK", "EVTV", "EXAI", "EXPR", "EYE", "EYEN", "EYPT", "FAMI", "FATE", "FBIO", "FBRX", "FCEL", "FCON", "FCRD", "FDMT", "FDP", "FENC", "FEXD", "FGEN", "FIXX", "FKWL", "FLGC", "FLGT", "FLUX", "FLXN", "FMTX", "FNCH", "FNHC", "FNKO", "FORW"]
TURBO_SYMBOLS = []

STRATEGY_CONFIG = {
    1: {"tag": "[P1-Classic]", "budget": 150},
    2: {"tag": "[P2-Classic]", "budget": 100},
    3: {"tag": "[P3-ORB]", "budget": 50},
    4: {"tag": "[P4-VWAP]", "budget": 50},
    5: {"tag": "[P5-Squat]", "budget": 50}
}

# ==========================================
# 3. 인프라 (ntfy, 시간, 웹서버)
# ==========================================
app = Flask(__name__)
@app.route('/')
def health(): return "Sm6+Sm7 V1.41 Active", 200

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def send_ntfy(msg):
    try: requests.post(NTFY_URL, data=msg.encode('utf-8'))
    except: pass

def get_kst_now():
    return datetime.utcnow() + timedelta(hours=9)

# ==========================================
# 4. 방어막 및 자산 배분 (70% 룰)
# ==========================================
def get_market_status():
    clock = api.get_clock()
    kst = get_kst_now()
    if 8 <= kst.hour < 18: return "REST", False
    if clock.is_open:
        time_since_open = (datetime.now(clock.timestamp.tzinfo) - clock.next_open + timedelta(days=1)).total_seconds()
        if 0 < time_since_open < 1800: return "REGULAR_SHIELD", False
        return "REGULAR", True
    if 18 <= kst.hour < 23:
        if kst.hour == 18 and kst.minute < 20: return "PRE_MARKET_SHIELD", False
        return "EXTENDED", True
    return "EXTENDED", True

def check_buying_power_limit(priority):
    acc = api.get_account()
    equity = float(acc.equity)
    cash = float(acc.non_marginable_buying_power)
    used_ratio = (equity - cash) / equity
    if used_ratio > 0.70 and priority >= 3: return False
    return True

# ==========================================
# 5. 사냥 엔진 (V1.41 미세조정: 타임컷 추가)
# ==========================================
def start_hunting(symbol):
    if symbol in active_positions:
        try:
            trade = api.get_latest_trade(symbol)
            curr_price = trade.p
            pos = active_positions[symbol]
            
            # 진입 시간 기록 (타임컷용)
            if 'entry_ts' not in pos: pos['entry_ts'] = time.time()
            
            pos['highest_price'] = max(pos.get('highest_price', curr_price), curr_price)
            profit = (curr_price - pos['entry_price']) / pos['entry_price']
            drop_from_top = (pos['highest_price'] - curr_price) / pos['highest_price']

            # [미세조정 1] 타임컷: 30분 경과 시 수익 0.5% 미만 탈출
            elapsed = time.time() - pos['entry_ts']
            if elapsed > 1800 and profit < 0.005:
                exit_trade(symbol, pos['qty'], profit, f"{pos['tag']} 타임컷(30m)")
                return

            if profit <= -0.045:
                exit_trade(symbol, pos['qty'], profit, f"{pos['tag']} 손절(-4.5%)")
            elif profit > 0.01 and drop_from_top >= 0.03:
                exit_trade(symbol, pos['qty'], profit, f"{pos['tag']} 추격익절")
        except: pass
        return

    try:
        bars = api.get_bars(symbol, tradeapi.TimeFrame.Minute * 5, limit=50).df
        if bars.empty: return
        df = bars.copy()
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        curr, prev = df.iloc[-1], df.iloc[-2]
        vol_avg = df['volume'].rolling(window=20).mean().iloc[-2]

        # 전략 필터
        vol_ok = curr['volume'] > (vol_avg * 0.7)
        box_breakout = curr['close'] > df['high'].iloc[-15:-1].max()
        rsi_up = curr['RSI'] > prev['RSI']
        orb_break = curr['close'] > df['high'].iloc[:5].max()
        vwap_cross = curr['close'] > (curr['VWAP'] * 1.0075)

        priority = 0
        if box_breakout and rsi_up and curr['close'] > prev['close'] * 1.05: priority = 1
        elif vol_ok and rsi_up and curr['close'] > prev['close'] * 1.05: priority = 2
        elif orb_break and curr['volume'] > vol_avg * 1.1: priority = 3
        elif vwap_cross: priority = 4
        elif curr['volume'] > vol_avg * 2 and abs(curr['close'] - prev['close']) / prev['close'] < 0.01: priority = 5

        if priority > 0:
            if not check_buying_power_limit(priority):
                reject_log.append(f"{symbol}: [현금부족] P{priority} 거부")
                return
            qty = int(STRATEGY_CONFIG[priority]['budget'] // curr['close'])
            if qty > 0:
                tag = STRATEGY_CONFIG[priority]['tag']
                api.submit_order(symbol=symbol, qty=qty, side='buy', type='market', time_in_force='gtc', extended_hours=True)
                active_positions[symbol] = {'entry_price': curr['close'], 'highest_price': curr['close'], 
                                           'priority': priority, 'qty': qty, 'tag': tag, 'entry_ts': time.time()}
                send_ntfy(f"🎯 {tag} 진입: {symbol} (${curr['close']})")
        elif symbol in BASE_SYMBOLS[:30]:
            reject_log.append(f"{symbol}: 지표미달 (RSI:{curr['RSI']:.1f})")
    except: pass

def exit_trade(symbol, qty, profit, reason):
    try:
        api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='gtc', extended_hours=True)
        send_ntfy(f"✅ [Sell] {symbol}\n사유: {reason}\n수익: {profit*100:.2f}%")
        trade_history.append({'symbol': symbol, 'profit': profit*100})
        if symbol in active_positions: del active_positions[symbol]
    except: pass

# ==========================================
# 6. 시스템 관리 (리포트 & 메인 루프)
# ==========================================
def report_system():
    last_h = -1
    last_d = -1
    while True:
        kst = get_kst_now()
        if kst.hour != last_h:
            send_ntfy(f"📡 [Sm6/7] {kst.strftime('%H:%M')} 가동 중")
            last_h = kst.hour
        if kst.hour == 9 and last_d != kst.day:
            if reject_log:
                send_ntfy(f"📋 [탈락 리포트]\n" + "\n".join(reject_log[-10:]))
                reject_log.clear()
            last_d = kst.day
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    threading.Thread(target=report_system, daemon=True).start()
    if auth_test():
        last_turbo_update = 0
        while True:
            try:
                status, can_trade = get_market_status()
                if status == "REST":
                    time.sleep(600); continue
                if not can_trade:
                    time.sleep(60); continue
                
                # [미세조정 2] 터보 레이더 10분 주기 업데이트
                if time.time() - last_turbo_update > 600:
                    assets = api.list_assets(status='active', asset_class='us_equity')
                    symbols = [a.symbol for a in assets if a.tradable][:200]
                    snaps = api.get_snapshots(symbols)
                    TURBO_SYMBOLS = [s for s, sn in snaps.items() if sn.daily_bar and (sn.latest_trade.p / sn.prev_daily_bar.c - 1) > 0.035]
                    last_turbo_update = time.time()

                for symbol in list(set(BASE_SYMBOLS + TURBO_SYMBOLS)):
                    start_hunting(symbol)
                    time.sleep(0.5)
            except Exception as e:
                print(f"Loop Error: {e}"); time.sleep(10)
