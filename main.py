import os
import time
import requests
import pandas as pd
import pandas_ta as ta
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
from pytz import timezone
from flask import Flask
import threading

# ==========================================
# 1. 설정 및 자가 진단
# ==========================================
API_KEY = "PKHQEN22KBWB2HSXRGMPWQ3QYL"
API_SECRET = "ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i"
BASE_URL = "https://paper-api.alpaca.markets"
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

reject_log = []
active_positions = {}
trade_history = []

# [오류수정 1] 타임존 정의 - utcnow()의 모호함을 해결
NY = timezone('America/New_York')
KST = timezone('Asia/Seoul')

def send_ntfy(msg):
    try: requests.post(NTFY_URL, data=msg.encode('utf-8'))
    except: pass

def auth_test():
    try:
        acc = api.get_account()
        if acc.status == 'ACTIVE':
            msg = f"✅ [V1.44 시작] 계좌 연결됨\nBP: ${float(acc.buying_power):,.2f}"
            send_ntfy(msg); return True
    except Exception as e:
        send_ntfy(f"❌ API 연결 실패: {e}"); return False

# ==========================================
# 2. 시장 상태 및 방어막 (시간 로직 정밀화)
# ==========================================
def get_market_status():
    now_ny = datetime.now(NY)
    now_kst = datetime.now(KST)
    clock = api.get_clock()
    
    # 1. 한국 시간 휴식 모드 (08:00 ~ 18:00)
    if 8 <= now_kst.hour < 18:
        return "REST", False
        
    # 2. 장중(Regular) 및 방어막
    if clock.is_open:
        # 본장 개장 시간 구하기
        opened_at = clock.next_open.replace(tzinfo=NY) if not clock.is_open else clock.timestamp.replace(tzinfo=NY)
        if (now_ny - opened_at).total_seconds() < 1800: # 30분 방어막
            return "REGULAR_SHIELD", False
        return "REGULAR", True
    
    # 3. 프리마켓/애프터마켓 (18:00 ~ 23:20 KST 방어막 포함)
    if 18 <= now_kst.hour < 23:
        if now_kst.hour == 18 and now_kst.minute < 20: 
            return "PRE_MARKET_SHIELD", False
    
    return "EXTENDED", True

def check_buying_power_limit(priority):
    acc = api.get_account()
    equity = float(acc.equity)
    cash = float(acc.non_marginable_buying_power)
    used_ratio = (equity - cash) / equity
    # 70% 이상 사용 시 P3~P6 진입 제한 (성민님 원칙)
    if used_ratio > 0.70 and priority >= 3: return False
    return True

# ==========================================
# 3. 사냥 엔진 (P1 ~ P6 전략 통합)
# ==========================================
def start_hunting(symbol):
    if symbol in active_positions:
        try:
            trade = api.get_latest_trade(symbol)
            curr_price = trade.p
            pos = active_positions[symbol]
            if 'entry_ts' not in pos: pos['entry_ts'] = time.time()
            
            pos['highest_price'] = max(pos.get('highest_price', curr_price), curr_price)
            profit = (curr_price - pos['entry_price']) / pos['entry_price']
            drop_from_top = (pos['highest_price'] - curr_price) / pos['highest_price']

            # 매도 로직 (타임컷 + 손절 + 추격익절)
            elapsed = time.time() - pos['entry_ts']
            if elapsed > 1800 and profit < 0.005: # [미세조정] 타임컷
                exit_trade(symbol, pos['qty'], profit, "타임컷(30m)")
                return
            if profit <= -0.045:
                exit_trade(symbol, pos['qty'], profit, "손절(-4.5%)")
            elif profit > 0.01 and drop_from_top >= 0.03:
                exit_trade(symbol, pos['qty'], profit, "추격익절")
        except: pass
        return

    try:
        # [오류수정 3] 데이터 유무 체크 강화
        bars = api.get_bars(symbol, tradeapi.TimeFrame.Minute * 5, limit=50).df
        if bars.empty: return
        
        df = bars.copy()
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        
        # P6용 스퀴즈 지표 계산
        bb = ta.bbands(df['close'], length=20, std=2)
        df['bb_u'], df['bb_l'] = bb['BBU_20_2.0'], bb['BBL_20_2.0']
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=20)
        df['kc_u'] = df['close'].rolling(20).mean() + (df['atr'] * 1.5)
        df['kc_l'] = df['close'].rolling(20).mean() - (df['atr'] * 1.5)

        curr, prev = df.iloc[-1], df.iloc[-2]
        vol_avg = df['volume'].rolling(window=20).mean().iloc[-2]

        priority = 0
        # P1: 박스 돌파 + RSI 상승 + 5% 급등
        if curr['close'] > df['high'].iloc[-15:-1].max() and curr['RSI'] > prev['RSI'] and curr['close'] > prev['close'] * 1.05: priority = 1
        # P2: 거래량 + RSI 상승 + 5% 급등
        elif curr['volume'] > (vol_avg * 0.7) and curr['RSI'] > prev['RSI'] and curr['close'] > prev['close'] * 1.05: priority = 2
        # P3: ORB (5분봉 돌파)
        elif curr['close'] > df['high'].iloc[:5].max() and curr['volume'] > vol_avg * 1.1: priority = 3
        # P4: VWAP 돌파
        elif curr['close'] > (curr['VWAP'] * 1.0075): priority = 4
        # P5: 매집 포착 (성민님 로직)
        elif curr['volume'] > (vol_avg * 2.0) and abs(curr['close'] - prev['close']) / prev['close'] < 0.01: priority = 5
        # P6: 스퀴즈 포착 (Bollinger inside Keltner)
        else:
            is_squeeze = (curr['bb_u'] < curr['kc_u']) and (curr['bb_l'] > curr['kc_l'])
            if is_squeeze and curr['volume'] > (vol_avg * 1.1): priority = 6

        if priority > 0:
            if not check_buying_power_limit(priority):
                if symbol in ["JTAI", "ROLR", "GWAV"]: reject_log.append(f"{symbol}: BP부족 P{priority}")
                return
            budget = 150 if priority <= 2 else 50
            qty = int(budget // curr['close'])
            if qty > 0:
                api.submit_order(symbol=symbol, qty=qty, side='buy', type='market', time_in_force='gtc', extended_hours=True)
                active_positions[symbol] = {'entry_price': curr['close'], 'highest_price': curr['close'], 'qty': qty, 'tag': f'[P{priority}]', 'entry_ts': time.time()}
                send_ntfy(f"🎯 진입: {symbol} (P{priority})")
        elif symbol in ["JTAI", "ROLR", "GWAV"]:
            reject_log.append(f"{symbol}: 지표미달(RSI:{curr['RSI']:.1f})")
    except: pass

def exit_trade(symbol, qty, profit, reason):
    try:
        api.submit_order(symbol=symbol, qty=qty, side='sell', type='market', time_in_force='gtc', extended_hours=True)
        send_ntfy(f"✅ 매도: {symbol}\n사유: {reason}\n익절: {profit*100:.2f}%")
        if symbol in active_positions: del active_positions[symbol]
    except: pass

# ==========================================
# 4. 시스템 관리 (리포트 오류 수정)
# ==========================================
def report_system():
    last_h = -1
    while True:
        now_kst = datetime.now(KST)
        if now_kst.hour != last_h:
            # [오류수정 2] 생존신고 시 로그 개수를 함께 보냄 (진행상황 확인용)
            send_ntfy(f"📡 [V1.44] {now_kst.strftime('%H:%M')} 가동중\n누적 로그: {len(reject_log)}건")
            last_h = now_kst.hour
            if now_kst.hour == 9: # 오전 9시 최종 리포트
                if reject_log:
                    send_ntfy(f"📋 [탈락 리포트]\n" + "\n".join(reject_log[-10:]))
                    reject_log.clear()
        time.sleep(60)

# ==========================================
# 5. 실행부 (뼈대 유지)
# ==========================================
app = Flask(__name__)
@app.route('/')
def health(): return "V1.44 Live", 200

BASE_SYMBOLS = ["ROLR", "JTAI", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "MGIH", "IMPP", "CING", "SNAL", "MRAI", "BRLS", "HUBC", "AGBA", "ICU", "TPST", "LGVN", "CNEY", "SCPX", "TCBP", "KITT", "RVSN", "SERV", "SMFL", "IVP", "WISA", "VHAI", "MGRM", "SPRC", "AENT", "AEI", "AEMD", "AEYE", "AEZS", "AFIB", "AIHS", "AIMD", "AITX", "AKAN", "AKBA", "AKTX", "ALBT", "ALDX", "ALOT", "ALPP", "ALRN", "ALVOP", "AMBO", "AMST", "ANIX", "ANY", "AOMR", "APDN", "APGN", "APLM", "APLT", "APTO", "APVO", "APWC", "AQB", "AQMS", "AQST", "ARAV", "ARBB", "ARBE", "ARBK", "ARCT", "ARDS", "ARDX", "AREB", "ARGX", "ARL", "ARMP", "ARQT", "ARSN", "ARTL", "ARTW", "ARVN", "ASNS", "ASPA", "ASPS", "ASRT", "ASRV", "ASST", "ASTI", "ASTR", "ASTS", "ASXC", "ATAI", "ATAK", "ATCG", "ATCP", "ATEC", "ATER", "ATGL", "ATNF", "ATNM", "ATNX", "ATOS", "ATPC", "ATRA", "ATRI", "ATRO", "ATXG", "AUBAP", "AUUD", "AVDL", "AVGR", "AVIR", "AVRO", "AVTX", "AVXL", "AWIN", "AWRE", "AXLA", "AXNX", "AXTI", "AYRO", "AYTU", "AZRE", "AZTR", "BANN", "BCAN", "BCDA", "BCEL", "BCOV", "BCSA", "BDRX", "BETS", "BFRI", "BGI", "BGLC", "BGM", "BHAT", "BIAF", "BIG", "BIOC", "BITF", "BKYI", "BLBX", "BLIN", "BLNK", "BLPH", "BLRX", "BLTE", "BLUE", "BMRA", "BNGO", "BNRG", "BNTC", "BOF", "BOSC", "BOXD", "BPT", "BRDS", "BRIB", "BRQS", "BRSH", "BRTX", "BSFC", "BSGM", "BTBD", "BTBT", "BTCS", "BTM", "BTOG", "BTTR", "BTTX", "BTU", "BURG", "BXRX", "BYFC", "BYRN", "BYSI", "BZFD", "CAPR", "CARV", "CASI", "CASS", "CATX", "CBAS", "CBIO", "CBMG", "CEMI", "CENN", "CENT", "CETY", "CEZA", "CFRX", "CGON", "CHNR", "CHRS", "CHSN", "CIDM", "CIFR", "CINC", "CIZN", "CJJD", "CKPT", "CLAR", "CLDI", "CLIR", "CLNE", "CLNN", "CLRB", "CLRO", "CLSD", "CLSK", "CLSN", "CLVR", "CLXT", "CMAX", "CMND", "CMRA", "CMRX", "CNET", "CNSP", "CNTX", "CNXA", "COCP", "CODX", "COGT", "COIN", "COMS", "CPHI", "CPIX", "CPOP", "CPTN", "CPX", "CRBP", "CRDL", "CRKN", "CRMD", "CRTD", "CRVO", "CRVS", "CSCW", "CSSEL", "CTIB", "CTIC", "CTLP", "CTMX", "CTNT", "CTRM", "CTSO", "CTXR", "CUEN", "CURI", "CVLB", "CVV", "CWBR", "CXAI", "CYAD", "CYAN", "CYBN", "CYCC", "CYCN", "CYN", "CYRN", "CYTK", "CYTO", "DARE", "DATS", "DBGI", "DCFC", "DCO", "DCTH", "DFFN", "DGHI", "DGLY", "DJV", "DLPN", "DMTK", "DNA", "DNMR", "DNUT", "DOMO", "DRMA", "DRRX", "DRTS", "DRUG", "DSCR", "DSGN", "DSKE", "DSSI", "DSX", "DTIL", "DTSS", "DVAX", "DXF", "DYAI", "DYNT", "DZZX", "EAAS", "EBIZ", "EBLU", "EBON", "ECOR", "EDBL", "EDSA", "EDTK", "EEIQ", "EFOI", "EGAN", "EGLX", "EGRX", "EHTH", "EIGI", "EKSO", "ELOX", "ELTK", "EMBK", "EMKR", "ENCP", "ENLV", "ENOB", "ENSC", "ENSV", "ENTG", "ENTX", "ENVB", "ENZC", "EOLS", "EOSE", "EPAY", "EPIX", "EPRX", "EQ", "EQOS", "ERAS", "ERC", "ERYP", "ESEA", "ESGC", "ESPR", "ETTX", "EVFM", "EVGN", "EVGO", "EVOK", "EVTV", "EXAI", "EXPR", "EYE", "EYEN", "EYPT", "FAMI", "FATE", "FBIO", "FBRX", "FCEL", "FCON", "FCRD", "FDMT", "FDP", "FENC", "FEXD", "FGEN", "FIXX", "FKWL", "FLGC", "FLGT", "FLUX", "FLXN", "FMTX", "FNCH", "FNHC", "FNKO", "FORW"]
TURBO_SYMBOLS = []

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    threading.Thread(target=report_system, daemon=True).start()
    if auth_test():
        last_turbo = 0
        while True:
            try:
                status, can_trade = get_market_status()
                if status == "REST":
                    time.sleep(600); continue
                if not can_trade:
                    time.sleep(60); continue
                
                # 터보 레이더 (10분 주기)
                if time.time() - last_turbo > 600:
                    try:
                        assets = api.list_assets(status='active', asset_class='us_equity')
                        symbols = [a.symbol for a in assets if a.tradable][:200]
                        snaps = api.get_snapshots(symbols)
                        TURBO_SYMBOLS = [s for s, sn in snaps.items() if sn.daily_bar and (sn.latest_trade.p / sn.prev_daily_bar.c - 1) > 0.035]
                        last_turbo = time.time()
                    except: pass

                for s in list(set(BASE_SYMBOLS + TURBO_SYMBOLS)):
                    start_hunting(s)
                    time.sleep(0.5)
            except Exception as e:
                print(f"Main Loop Error: {e}"); time.sleep(10)
