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

# [1] 보안 및 환경 설정
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_API_SECRET")
BASE_URL = "https://paper-api.alpaca.markets"
NTFY_URL = os.getenv("NTFY_URL", "https://ntfy.sh/sungmin_ssk_7")

# 생존 로직: 터미널 로그 Clean 유지
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
        msg = "✅ [인증] API 성공 | sm7 무한사냥(초안정) 엔진 가동"
        log(msg); send_ntfy(msg)
        return True
    except Exception as e:
        send_ntfy(f"❌ [경고] API 인증 실패: {e}"); return False

# ==========================================
# 2. 핵심 주문 로직 (설거지 방지/IOC/GTC) - 100% 유지
# ==========================================
def smart_buy(symbol, priority, tag, detect_price, is_extended):
    try:
        if not check_buying_power_limit(priority): return
        
        # [설거지 방지]: 감지 시점보다 2% 초과 상승 시 즉시 중단
        current_snap = api.get_snapshot(symbol)
        realtime_price = current_snap.latest_trade.p
        if realtime_price > detect_price * 1.02:
            log(f"🚫 {symbol} 설거지 방지 작동 (감지대비 +2% 초과)")
            return

        limit_price = round(realtime_price * 1.01, 2)
        budget = 150 if priority == 1 else (100 if priority == 2 else 50)
        qty = int(budget // limit_price)
        if qty <= 0: return

        # [IOC 주문]: 즉시 체결 안 되면 취소하여 주문 꼬임 방지
        def place_order():
            order = api.submit_order(
                symbol=symbol, qty=qty, side='buy', type='limit',
                limit_price=limit_price, time_in_force='ioc', 
                extended_hours=is_extended
            )
            time.sleep(2.0) # 안정성을 위해 대기시간 1.5 -> 2.0초 상향
            return api.get_order(order.id)

        order_info = place_order()
        if order_info.status != 'filled':
            log(f"⚠️ {symbol} 1차 실패, 재시도 중...")
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

# ==========================================
# 3. 분석 및 필터링 (P1~P5 통합) - 100% 유지
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
    try:
        acc = api.get_account()
        equity, cash = float(acc.equity), float(acc.non_marginable_buying_power)
        # [70% 룰]: 자산 70% 이상 사용 시 P3~P5 차단
        if (equity - cash) / equity > 0.70 and priority >= 3:
            reject_log.append(f"{datetime.now(KST).strftime('%H:%M')} BP부족(P{priority})")
            return False
        return True
    except: return False

def analyze_and_trade(symbol, curr_price, is_extended):
    if symbol in active_positions:
        pos = active_positions[symbol]
        pos['highest_price'] = max(pos.get('highest_price', curr_price), curr_price)
        profit = (curr_price - pos['entry_price']) / pos['entry_price']
        drop_from_top = (pos['highest_price'] - curr_price) / pos['highest_price']
        elapsed = time.time() - pos['entry_ts']
        # 익절/손절/타임컷 로직 유지
        if profit <= -0.045: exit_trade(symbol, pos['qty'], profit, "손절(-4.5%)", is_extended)
        elif profit > 0.01 and drop_from_top >= 0.03: exit_trade(symbol, pos['qty'], profit, "추격익절", is_extended)
        elif elapsed > 1800 and profit < 0.005: exit_trade(symbol, pos['qty'], profit, "타임컷", is_extended)
        return
    
    bars = None
    for _ in range(3):
        try: bars = api.get_bars(symbol, tradeapi.TimeFrame.Minute * 5, limit=30).df; break
        except: time.sleep(2)
    if bars is None or bars.empty or len(bars) < 20: return
    
    try:
        df = bars.copy()
        df['RSI'] = ta.rsi(df['close'], length=14); df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        curr, prev = df.iloc[-1], df.iloc[-2]
        vol_avg = max(df['volume'].rolling(window=20).mean().iloc[-2], 1)
        if is_extended: vol_avg *= 0.3
        
        priority = 0; tag = ""
        # P1~P5 통합 필터링 (하나만 걸려도 통과)
        if curr['close'] > df['high'].iloc[-15:-1].max() and curr['RSI'] > prev['RSI'] and curr['close'] > prev['close'] * 1.05:
            priority = 1; tag = "[P1-Strict]"
        elif curr['volume'] > (vol_avg * 0.6) and curr['RSI'] > prev['RSI'] and curr['close'] > prev['close'] * 1.05:
            priority = 2; tag = "[P2-Mid]"
        elif curr['close'] > df['high'].iloc[:5].max() and curr['volume'] > vol_avg * 1.1:
            priority = 3; tag = "[P3-ORB]"
        elif curr['close'] > (curr['VWAP'] * 1.0075):
            priority = 4; tag = "[P4-VWAP]"
        elif curr['volume'] > (vol_avg * 2.0) and abs(curr['close'] - prev['close']) / prev['close'] < 0.01:
            priority = 5; tag = "[P5-Squat]"
            
        if priority > 0:
            smart_buy(symbol, priority, tag, curr_price, is_extended)
    except: pass

# ==========================================
# 4. 안정화 메인 루프 (누락 방지)
# ==========================================
app = Flask(__name__)
@app.route('/')
def health(): return "sm7 Stable Hunter V1.8 - Online", 200

def report_system():
    while True:
        try:
            now_kst = datetime.now(KST)
            if (now_kst.weekday() == 5 and now_kst.hour >= 8) or (now_kst.weekday() == 6) or (now_kst.weekday() == 0 and now_kst.hour < 8):
                if now_kst.hour == 10 and now_kst.minute == 0:
                    send_ntfy("😴 주말 계좌 복기: 시스템 휴식 중"); time.sleep(60)
                time.sleep(1800); continue
            if now_kst.hour == 9 and now_kst.minute == 0:
                msg = f"📋 [sm7 탈락 리포트]\n- 현재 포지션: {list(active_positions.keys())}\n- 주요 거절 사유: {reject_log[-10:]}"
                send_ntfy(msg); reject_log.clear(); time.sleep(60)
        except: pass
        time.sleep(60)

BASE_SYMBOLS = ["ROLR", "BNAI", "RXT", "BATL", "TMDE", "INDO", "SVRN", "DFLI", "JTAI", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "MGIH", "IMPP", "CING", "SNAL", "MRAI", "BRLS", "HUBC", "AGBA", "ICU", "TPST", "LGVN", "CNEY", "SCPX", "TCBP", "KITT", "RVSN", "SERV", "SMFL", "IVP", "WISA", "VHAI", "MGRM", "SPRC", "AENT", "AEI", "AEMD", "AEYE", "AEZS", "AFIB", "AIHS", "AIMD", "AITX", "AKAN", "AKBA", "AKTX", "ALBT", "ALDX", "ALOT", "ALPP", "ALRN", "ALVOP", "AMBO", "AMST", "ANIX", "ANY", "AOMR", "APDN", "APGN", "APLM", "APLT", "APTO", "APVO", "APWC", "AQB", "AQMS", "AQST", "ARAV", "ARBB", "ARBE", "ARBK", "ARCT", "ARDS", "ARDX", "AREB", "ARGX", "ARL", "ARMP", "ARQT", "ARSN", "ARTL", "ARTW", "ARVN", "ASNS", "ASPA", "ASPS", "ASRT", "ASRV", "ASST", "ASTI", "ASTR", "ASTS", "ASXC", "ATAI", "ATAK", "ATCG", "ATCP", "ATEC", "ATER", "ATGL", "ATNF", "ATNM", "ATNX", "ATOS", "ATPC", "ATRA", "ATRI", "ATRO", "ATXG", "AUBAP", "AUUD", "AVDL", "AVGR", "AVIR", "AVRO", "AVTX", "AVXL", "AWIN", "AWRE", "AXLA", "AXNX", "AXTI", "AYRO", "AYTU", "AZRE", "AZTR", "BANN", "BCAN", "BCDA", "BCEL", "BCOV", "BCSA", "BDRX", "BETS", "BFRI", "BGI", "BGLC", "BGM", "BHAT", "BIAF", "BIG", "BIOC", "BITF", "BKYI", "BLBX", "BLIN", "BLNK", "BLPH", "BLRX", "BLTE", "BLUE", "BMRA", "BNGO", "BNRG", "BNTC", "BOF", "BOSC", "BOXD", "BPT", "BRDS", "BRIB", "BRQS", "BRSH", "BRTX", "BSFC", "BSGM", "BTBD", "BTBT", "BTCS", "BTM", "BTOG", "BTTR", "BTTX", "BTU", "BURG", "BXRX", "BYFC", "BYRN", "BYSI", "BZFD", "CAPR", "CARV", "CASI", "CASS", "CATX", "CBAS", "CBIO", "CBMG", "CEMI", "CENN", "CENT", "CETY", "CEZA", "CFRX", "CGON", "CHNR", "CHRS", "CHSN", "CIDM", "CIFR", "CINC", "CIZN", "CJJD", "CKPT", "CLAR", "CLDI", "CLIR", "CLNE", "CLNN", "CLRB", "CLRO", "CLSD", "CLSK", "CLSN", "CLVR", "CLXT", "CMAX", "CMND", "CMRA", "CMRX", "CNET", "CNSP", "CNTX", "CNXA", "COCP", "CODX", "COGT", "COIN", "COMS", "CPHI", "CPIX", "CPOP", "CPTN", "CPX", "CRBP", "CRDL", "CRKN", "CRMD", "CRTD", "CRVO", "CRVS", "CSCW", "CSSEL", "CTIB", "CTIC", "CTLP", "CTMX", "CTNT", "CTRM", "CTSO", "CTXR", "CUEN", "CURI", "CVLB", "CVV", "CWBR", "CXAI", "CYAD", "CYAN", "CYBN", "CYCC", "CYCN", "CYN", "CYRN", "CYTO", "DARE", "DATS", "DBGI", "DCFC", "DCO", "DCTH", "DFFN", "DGHI", "DGLY", "DJV", "DLPN", "DMTK", "DNA", "DNMR", "DNUT", "DOMO", "DRMA", "DRRX", "DRTS", "DRUG", "DSCR", "DSGN", "DSKE", "DSSI", "DSX", "DTIL", "DTSS", "DVAX", "DXF", "DYAI", "DYNT", "DZZX"]

def main_trading_loop():
    time.sleep(10) # 서버 안정화 대기
    send_ntfy("🚀 sm7-위대한 항로 가동\n[무한 사냥 + 초안정 모드]")
    if auth_test():
        threading.Thread(target=report_system, daemon=True).start()
        while True:
            try:
                status, can_trade = get_market_status()
                if status == "REST": time.sleep(600); continue
                if "SHIELD" in status: time.sleep(30); continue 
                
                # [무한 사냥 모드 유지]: 매 루프마다 실시간 급등주 상위 10개 수혈
                dynamic_symbols = []
                try:
                    movers = api.get_movers(symbol_set='all', top_n=10)
                    dynamic_symbols = [m.symbol for m in movers]
                except: pass

                hunting_list = list(set(BASE_SYMBOLS + dynamic_symbols))
                
                chunk_size = 50 # 부하 분산
                for i in range(0, len(hunting_list), chunk_size):
                    chunk = hunting_list[i:i + chunk_size]
                    try: snaps = api.get_snapshots(chunk)
                    except: time.sleep(10); continue
                    
                    for symbol in chunk:
                        if symbol not in snaps or not snaps[symbol].latest_trade: continue
                        snap = snaps[symbol]
                        curr_price = snap.latest_trade.p
                        prev_close = snap.prev_daily_bar.c if snap.prev_daily_bar else curr_price
                        
                        # 3% 이상 변동 시 정밀 분석
                        if (curr_price / prev_close - 1) > 0.03 or symbol in active_positions:
                            analyze_and_trade(symbol, curr_price, (status == "EXTENDED"))
                    
                    # [안정권 핵심]: 묶음 사이 2초 휴식으로 Flask 포트 개방 보장
                    time.sleep(2.0)
                    
            except Exception as e:
                log(f"Loop Error: {e}"); time.sleep(20)

if __name__ == "__main__":
    # 트레이딩 스레드 시작
    threading.Thread(target=main_trading_loop, daemon=True).start()
    # Flask 서버 시작 (UptimeRobot 대응)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
