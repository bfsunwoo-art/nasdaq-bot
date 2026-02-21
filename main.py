import os
import time
import requests
import pandas as pd
import pandas_ta as ta
import alpaca_trade_api as tradeapi
from datetime import datetime
from pytz import timezone
from flask import Flask
import threading
import sys

# [1] 기본 및 보안 설정
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_API_SECRET")
BASE_URL = "https://paper-api.alpaca.markets"
NTFY_URL = os.getenv("NTFY_URL", "https://ntfy.sh/sungmin_ssk_7")

sys.stderr = open(os.devnull, 'w')
api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

reject_log = []
active_positions = {}
KST = timezone('Asia/Seoul')

def send_ntfy(msg):
    try: requests.post(NTFY_URL, data=msg.encode('utf-8'), timeout=5)
    except: pass

def log(msg):
    now_kst = datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now_kst}] {msg}", flush=True)

def auth_test():
    try:
        api.get_account()
        msg = "✅ [인증] API 성공 | sm7 무한사냥 V3 (사냥꾼의 감각) 가동"
        log(msg); send_ntfy(msg)
        return True
    except Exception as e:
        send_ntfy(f"❌ [경고] API 인증 실패: {e}"); return False

# ==========================================
# 2. 리포트 및 휴식 로직 (유지)
# ==========================================
def report_system():
    log("📊 리포트 스케줄러 가동")
    while True:
        try:
            now_kst = datetime.now(KST)
            # 주말 휴식 알림 (토요일 오전 10시)
            if now_kst.weekday() == 5 and now_kst.hour == 10 and now_kst.minute == 0:
                send_ntfy("😴 주말 계좌 복기: 시스템 휴식 중")
                time.sleep(60)
            
            # 매일 아침 9시 요약 리포트
            if now_kst.hour == 9 and now_kst.minute == 0:
                pos_list = list(active_positions.keys())
                msg = f"📋 [sm7 아침 리포트]\n- 현재 포지션: {pos_list if pos_list else '없음'}\n- 주요 거절 사유(최근 10건): {reject_log[-10:]}"
                send_ntfy(msg)
                reject_log.clear() # 리포트 후 로그 비우기
                time.sleep(60)
        except Exception as e:
            log(f"Report Error: {e}")
        time.sleep(30)

# ==========================================
# 3. 매매 전략 로직 및 리스크 관리
# ==========================================
def get_market_status():
    now_kst = datetime.now(KST)
    try: clock = api.get_clock()
    except: return "ERROR", False
    if now_kst.hour == 18 and 0 <= now_kst.minute < 20: return "PRE_SHIELD", False
    if (now_kst.hour == 23 and now_kst.minute >= 30) or (now_kst.hour == 0 and now_kst.minute < 1): return "REG_SHIELD", False
    if 8 <= now_kst.hour < 18: return "REST", False
    return ("REGULAR" if clock.is_open else "EXTENDED"), True

def check_buying_power_limit(priority):
    """ (70% 룰) P2를 위한 현금 30% 상시 확보 """
    try:
        acc = api.get_account()
        equity, cash = float(acc.equity), float(acc.non_marginable_buying_power)
        usage_ratio = (equity - cash) / equity
        
        # 총 자산 대비 매수 비중이 70% 초과 시 P3, P4, P5 진입 차단 (P1, P2만 허용)
        if usage_ratio > 0.70 and priority >= 3:
            reject_log.append(f"{datetime.now(KST).strftime('%H:%M')} BP부족(70%룰 차단-P{priority})")
            return False
        return True
    except: return False

def smart_buy(symbol, priority, tag, detect_price, is_extended, budget):
    """ 설거지 방지 및 IOC 기반 스마트 체결 """
    try:
        if not check_buying_power_limit(priority): return
        current_snap = api.get_snapshot(symbol)
        realtime_price = current_snap.latest_trade.p
        
        # [Anti-Dump] 포착가 대비 실제 주문 시점 가격이 2% 이상 높으면 추격 매수 포기
        if realtime_price > detect_price * 1.02:
            log(f"🚫 {symbol} 고점 설거지 방지 작동 (포착:{detect_price} / 현재:{realtime_price})")
            return
            
        limit_price = round(realtime_price * 1.01, 2)
        qty = int(budget // limit_price)
        if qty <= 0: return
        
        def place_order():
            # 모든 장 지정가 + IOC (미체결 잔량 즉시 취소)
            order = api.submit_order(symbol=symbol, qty=qty, side='buy', type='limit',
                limit_price=limit_price, time_in_force='ioc', extended_hours=is_extended)
            time.sleep(2.0)
            return api.get_order(order.id)
            
        order_info = place_order()
        if order_info.status != 'filled': # 1회 한정 재시도 (주문 꼬임 방지)
            log(f"⚠️ {symbol} IOC 미체결, 1회 재시도...")
            order_info = place_order()
            
        if order_info.status == 'filled':
            send_ntfy(f"🎯 {tag} 체결: {symbol}\n단가: ${order_info.filled_avg_price}\n설거지방지: 통과")
            active_positions[symbol] = {
                'entry_price': float(order_info.filled_avg_price),
                'highest_price': float(order_info.filled_avg_price),
                'qty': qty, 'entry_ts': time.time(), 'tag': tag
            }
    except Exception as e: log(f"Buy Error {symbol}: {e}")

def exit_trade(symbol, qty, profit, reason, is_extended):
    try:
        trade = api.get_latest_trade(symbol)
        limit_price = round(trade.p * 0.985, 2)
        api.submit_order(symbol=symbol, qty=qty, side='sell', type='limit',
                         limit_price=limit_price, time_in_force='gtc', extended_hours=is_extended)
        tag = active_positions[symbol].get('tag', '')
        send_ntfy(f"✅ 매도: {symbol} {tag}\n사유: {reason}\n수익: {profit*100:.2f}%")
        if symbol in active_positions: del active_positions[symbol]
    except: pass

def analyze_and_trade(symbol, curr_price, prev_close, snap, is_extended):
    # [출구 전략 (Exit Logic)]
    if symbol in active_positions:
        pos = active_positions[symbol]
        pos['highest_price'] = max(pos.get('highest_price', curr_price), curr_price)
        profit = (curr_price - pos['entry_price']) / pos['entry_price']
        drop_from_top = (pos['highest_price'] - curr_price) / pos['highest_price']
        elapsed = time.time() - pos['entry_ts']
        
        if profit <= -0.045: exit_trade(symbol, pos['qty'], profit, "본절 손절(-4.5%)", is_extended)
        elif profit > 0.01 and drop_from_top >= 0.03: exit_trade(symbol, pos['qty'], profit, "추격 익절(Trailing)", is_extended)
        elif elapsed > 1800 and profit < 0.005: exit_trade(symbol, pos['qty'], profit, "타임컷(30분 경과)", is_extended)
        return
        
    # [사냥꾼의 감각 진입 전략 (Entry Logic)]
    try:
        # P1, P4, P5 조건 확인을 위해 1분봉 데이터 60개 호출 (정밀도 상승)
        bars = api.get_bars(symbol, tradeapi.TimeFrame.Minute, limit=60).df
        if bars is None or bars.empty or len(bars) < 20: return
        df = bars.copy()
        
        # 보조지표 계산
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['vol_avg_20'] = df['volume'].rolling(window=20).mean()
        # 볼린저 밴드 계산 (기간 20)
        df['SMA20'] = df['close'].rolling(window=20).mean()
        df['STD20'] = df['close'].rolling(window=20).std()
        df['BB_WIDTH'] = (4 * df['STD20']) / df['SMA20'] 

        curr = df.iloc[-1]
        prev1 = df.iloc[-2]
        prev2 = df.iloc[-3]
        
        priority = 0; tag = ""; budget = 0
        now_kst = datetime.now(KST)

        # 공통 수급 데이터
        today_vol = snap.daily_bar.v if snap.daily_bar else 0
        prev_daily_vol = snap.prev_daily_bar.v if snap.prev_daily_bar else 1

        # --- P2: 수급의 지배 (최우선 순위 판별) ---
        is_premarket_time = (18 <= now_kst.hour <= 23)
        if is_premarket_time and today_vol > (prev_daily_vol * 0.5):
            priority = 2
            tag = "[P2-수급지배]"
            budget = 150 if now_kst.hour >= 23 else 100 # 본장 직전 집중 배팅
            
        # --- P1: 이성적 돌파 ---
        elif (prev1['close'] > prev1['open']) and (curr['volume'] > curr['vol_avg_20'] * 1.5):
            if 64 <= curr['RSI'] <= 70:
                priority = 1; tag = "[P1-돌파(100%)]"; budget = 100
            elif 70 < curr['RSI'] <= 77:
                priority = 1; tag = "[P1-돌파(70%)]"; budget = 70

        # --- P3: 광기의 눌림목 ---
        elif curr_price > prev_close * 1.5: # 당일 50% 이상 폭등 확인
            recent_low = df['low'].tail(20).min() # 최근 파동의 저가 근접
            if curr_price <= recent_low * 1.02:
                priority = 3; tag = "[P3-눌림목]"; budget = 50 # 고정 예산

        # --- P4: 억눌림 ---
        elif priority == 0:
            range_10m = (df['high'].tail(10).max() - df['low'].tail(10).min()) / curr_price
            is_bb_min = curr['BB_WIDTH'] <= df['BB_WIDTH'].tail(60).min() * 1.05 # 1시간 내 최소 수준
            is_vol_surge = curr['volume'] > curr['vol_avg_20'] * 1.8
            is_near_high = curr_price >= df['high'].tail(60).max() * 0.99
            
            if range_10m < 0.01 and is_bb_min and is_vol_surge and is_near_high:
                priority = 4; tag = "[P4-억눌림]"; budget = 100

        # --- P5: 포모 헌터 ---
        elif curr['volume'] > prev1['volume'] > prev2['volume']:
            nearest_rf = round(curr_price * 2) / 2 # 라운드 피겨 ($0.5, $1.0, $1.5 등)
            if nearest_rf > 0 and abs(curr_price - nearest_rf) / nearest_rf <= 0.005:
                priority = 5; tag = "[P5-포모]"; budget = 100
                
        # 조건 달성 시 매수 트리거
        if priority > 0: 
            smart_buy(symbol, priority, tag, curr_price, is_extended, budget)
    except: pass

# ==========================================
# 4. 메인 트레이딩 엔진
# ==========================================
BASE_SYMBOLS = ["ROLR", "BNAI", "RXT", "BATL", "TMDE", "INDO", "SVRN", "DFLI", "JTAI", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "MGIH", "IMPP", "CING", "SNAL", "MRAI", "BRLS", "HUBC", "AGBA", "ICU", "TPST", "LGVN", "CNEY", "SCPX", "TCBP", "KITT", "RVSN", "SERV", "SMFL", "IVP", "WISA", "VHAI", "MGRM", "SPRC", "AENT", "AEI", "AEMD", "AEYE", "AEZS", "AFIB", "AIHS", "AIMD", "AITX", "AKAN", "AKBA", "AKTX", "ALBT", "ALDX", "ALOT", "ALPP", "ALRN", "ALVOP", "AMBO", "AMST", "ANIX", "ANY", "AOMR", "APDN", "APGN", "APLM", "APLT", "APTO", "APVO", "APWC", "AQB", "AQMS", "AQST", "ARAV", "ARBB", "ARBE", "ARBK", "ARCT", "ARDS", "ARDX", "AREB", "ARGX", "ARL", "ARMP", "ARQT", "ARSN", "ARTL", "ARTW", "ARVN", "ASNS", "ASPA", "ASPS", "ASRT", "ASRV", "ASST", "ASTI", "ASTR", "ASTS", "ASXC", "ATAI", "ATAK", "ATCG", "ATCP", "ATEC", "ATER", "ATGL", "ATNF", "ATNM", "ATNX", "ATOS", "ATPC", "ATRA", "ATRI", "ATRO", "ATXG", "AUBAP", "AUUD", "AVDL", "AVGR", "AVIR", "AVRO", "AVTX", "AVXL", "AWIN", "AWRE", "AXLA", "AXNX", "AXTI", "AYRO", "AYTU", "AZRE", "AZTR", "BANN", "BCAN", "BCDA", "BCEL", "BCOV", "BCSA", "BDRX", "BETS", "BFRI", "BGI", "BGLC", "BGM", "BHAT", "BIAF", "BIG", "BIOC", "BITF", "BKYI", "BLBX", "BLIN", "BLNK", "BLPH", "BLRX", "BLTE", "BLUE", "BMRA", "BNGO", "BNRG", "BNTC", "BOF", "BOSC", "BOXD", "BPT", "BRDS", "BRIB", "BRQS", "BRSH", "BRTX", "BSFC", "BSGM", "BTBD", "BTBT", "BTCS", "BTM", "BTOG", "BTTR", "BTTX", "BTU", "BURG", "BXRX", "BYFC", "BYRN", "BYSI", "BZFD", "CAPR", "CARV", "CASI", "CASS", "CATX", "CBAS", "CBIO", "CBMG", "CEMI", "CENN", "CENT", "CETY", "CEZA", "CFRX", "CGON", "CHNR", "CHRS", "CHSN", "CIDM", "CIFR", "CINC", "CIZN", "CJJD", "CKPT", "CLAR", "CLDI", "CLIR", "CLNE", "CLNN", "CLRB", "CLRO", "CLSD", "CLSK", "CLSN", "CLVR", "CLXT", "CMAX", "CMND", "CMRA", "CMRX", "CNET", "CNSP", "CNTX", "CNXA", "COCP", "CODX", "COGT", "COIN", "COMS", "CPHI", "CPIX", "CPOP", "CPTN", "CPX", "CRBP", "CRDL", "CRKN", "CRMD", "CRTD", "CRVO", "CRVS", "CSCW", "CSSEL", "CTIB", "CTIC", "CTLP", "CTMX", "CTNT", "CTRM", "CTSO", "CTXR", "CUEN", "CURI", "CVLB", "CVV", "CWBR", "CXAI", "CYAD", "CYAN", "CYBN", "CYCC", "CYCN", "CYN", "CYRN", "CYTO", "DARE", "DATS", "DBGI", "DCFC", "DCO", "DCTH", "DFFN", "DGHI", "DGLY", "DJV", "DLPN", "DMTK", "DNA", "DNMR", "DNUT", "DOMO", "DRMA", "DRRX", "DRTS", "DRUG", "DSCR", "DSGN", "DSKE", "DSSI", "DSX", "DTIL", "DTSS", "DVAX", "DXF", "DYAI", "DYNT", "DZZX"]

def main_trading_loop():
    time.sleep(15)
    if auth_test():
        threading.Thread(target=report_system, daemon=True).start()
        while True:
            try:
                status, can_trade = get_market_status()
                if status == "REST": time.sleep(600); continue
                if "SHIELD" in status: time.sleep(30); continue 
                
                try:
                    movers = api.get_movers(symbol_set='all', top_n=10)
                    dynamic_symbols = [m.symbol for m in movers]
                except: dynamic_symbols = []
                
                hunting_list = list(set(BASE_SYMBOLS + dynamic_symbols))
                chunk_size = 40
                for i in range(0, len(hunting_list), chunk_size):
                    chunk = hunting_list[i:i + chunk_size]
                    try: snaps = api.get_snapshots(chunk)
                    except: time.sleep(5); continue
                    
                    for symbol in chunk:
                        if symbol not in snaps or not snaps[symbol].latest_trade: continue
                        snap = snaps[symbol]
                        curr_price = snap.latest_trade.p
                        prev_close = snap.prev_daily_bar.c if snap.prev_daily_bar else curr_price
                        
                        if (curr_price / prev_close - 1) > 0.03 or symbol in active_positions:
                            # snap 데이터를 analyze_and_trade로 넘겨 P2 수급 계산에 활용
                            analyze_and_trade(symbol, curr_price, prev_close, snap, (status == "EXTENDED"))
                    
                    # 🛡️ API Rate Limit 방지: 무료 티어 호출 제한을 피하기 위해 2.5초 -> 3.5초로 연장
                    time.sleep(3.5)
            except Exception as e:
                log(f"Loop 대기열 Error: {e}"); time.sleep(20)

# ==========================================
# 5. Flask 및 Gunicorn 통합 실행 (최종 확정본)
# ==========================================
app = Flask(__name__)

@app.route('/')
def health():
    now = datetime.now(KST).strftime('%H:%M:%S')
    pos_list = list(active_positions.keys())
    return f"<h3>sm7 V3 Full-Spec (Hunter's Instinct)</h3>Time: {now}<br>Pos: {pos_list if pos_list else 'None'}<br>Status: Hunting", 200

# [핵심] Gunicorn은 이 파일을 불러올 때 '전역 변수' 구역을 실행합니다.
# 따라서 엔진 시작 로직을 if __name__ 외부로 꺼내야 합니다.
def start_engine():
    if not any(t.name == "TradingEngine" for t in threading.enumerate()):
        log("🚀 [System] Gunicorn 환경 엔진 가동 시퀀스 시작...")
        engine = threading.Thread(target=main_trading_loop, name="TradingEngine", daemon=True)
        engine.start()

# 파일을 읽자마자 즉시 엔진 실행
start_engine()

if __name__ == "__main__":
    # 로컬 테스트용
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
