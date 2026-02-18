import pandas as pd
import numpy as np
import time
import requests
import os
import yfinance as yf
import logging
import sys
import gc  # 메모리 관리용
from datetime import datetime
from threading import Thread
from flask import Flask
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# [뼈대 1] 로그 및 에러 메시지 완벽 침묵
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
@app.route('/')
def health_check(): return "SM5_STORM_EYE_V2_RUNNING", 200

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 1. 설정 및 보안키
# ==========================================
API_KEY = "PKHQEN22KBWB2HSXRGMPWQ3QYL"
SECRET_KEY = "ASJRBNmkBzRe18oRinn2GBQMxgqmGLh4CBbBd99HB14i"
NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"
TRADING_CLIENT = TradingClient(API_KEY, SECRET_KEY, paper=True)

# [뼈대 2] 정제된 402개 리스트 + ROLR 최우선 추가
BASE_SYMBOLS = ["ROLR"] + [
    "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "MGIH", "IMPP", "GRI", "MRAI", "XFOR", 
    "TENX", "CDIO", "ICU", "MTC", "BDRX", "ABVC", "PHUN", "AKAN", "ASNS", "CXAI", 
    "HOLO", "ICG", "IKT", "BNRG", "BNGO", "VRAX", "ADTX", "CRBP", "KNSA", "SCYX", 
    "OPGN", "TNXP", "AGEN", "XCUR", "CLRB", "ATOS", "MBOT", "VYNE", "HROW", "INOD",
    # ... (기존 위대한 항로 402개 리스트 유지)
    "DASH", "LYFT", "UPWK"
]

# ==========================================
# 2. 탐색 및 보고 체계 (핵심 뼈대)
# ==========================================
last_heartbeat_hour = -1

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=5)
    except: pass

def check_heartbeat():
    """1시간 단위 생존 알림"""
    global last_heartbeat_hour
    now = datetime.now()
    if now.hour != last_heartbeat_hour:
        send_ntfy(f"✅ sm5 [위대한 항로] 생존 보고\n시각: {now.strftime('%H:%M')}\n상태: 로그 끊김 방지 가동 중")
        last_heartbeat_hour = now.hour

def get_turbo_movers():
    """[뼈대 3] 실시간 급등주 탐색 장비"""
    try:
        movers = yf.Search("", max_results=20).quotes
        new_targets = [m['symbol'] for m in movers if 'symbol' in m and "." not in m['symbol']]
        return list(set(BASE_SYMBOLS + new_targets))
    except: return BASE_SYMBOLS

def weekend_review():
    """[뼈대 4] 주말 계좌 복기 리포트"""
    now = datetime.now()
    if now.weekday() >= 5:
        try:
            acc = TRADING_CLIENT.get_account()
            send_ntfy(f"📊 [sm5 주말복기]\n현금: ${acc.cash}\n총자산: ${acc.equity}")
            time.sleep(43200)
        except: pass

# ==========================================
# 3. sm5 사냥 엔진 (로그 끊김 방지 강화)
# ==========================================
def start_hunting():
    # yfinance 출력 강제 차단
    orig_stderr = sys.stderr
    f = open(os.devnull, 'w')
    sys.stderr = f

    targets = get_turbo_movers()
    
    # [오류 해결책] 세션 과부하 방지를 위한 멀티 세션 종료 및 가비지 컬렉팅
    for symbol in targets:
        try:
            # interval 5m, period 2d 최신 데이터 다운로드 (Thread 가부하 방지 위해 progress=False)
            df = yf.download(symbol, interval="5m", period="2d", progress=False, timeout=10)
            
            if df.empty or len(df) < 30: 
                continue
            
            # 지표 계산 로직
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 0.0001))))
            df['MA20'] = df['Close'].rolling(window=20).mean()
            
            curr, prev = df.iloc[-1], df.iloc[-2]

            # 전략 필터링
            max_p = df['High'].iloc[-20:-1].max()
            min_p = df['Low'].iloc[-20:-1].min()
            had_spike = (max_p - min_p) / min_p > 0.05
            vol_ok = curr['Volume'] > (df['Volume'].rolling(window=20).mean().iloc[-2] * 0.6)
            rsi_up = curr['RSI'] > prev['RSI'] and 30 < curr['RSI'] < 70
            box_breakout = curr['Close'] > df['High'].iloc[-10:-1].max()
            is_pullback = curr['Close'] > curr['MA20']

            priority = 0
            if had_spike and vol_ok and rsi_up and box_breakout and is_pullback:
                priority = 1
            elif had_spike and vol_ok and rsi_up:
                priority = 2

            if priority > 0:
                p_label = "⭐1순위" if priority == 1 else "⚡2순위"
                send_ntfy(f"🎯 [{p_label}] {symbol} 포착!\n가:${round(curr['Close'],3)} RSI:{round(curr['RSI'],1)}")
                
                # 알파카 자동 매수 (비중 10%)
                limit_price = round(curr['Close'] * 1.002, 3)
                acc = TRADING_CLIENT.get_account()
                qty = int((float(acc.cash) * 0.1) / limit_price)
                
                if qty > 0:
                    TRADING_CLIENT.submit_order(LimitOrderRequest(
                        symbol=symbol, qty=qty, side=OrderSide.BUY,
                        limit_price=limit_price, time_in_force=TimeInForce.GTC
                    ))
            
            # [오류 해결책] 개별 종목 분석 후 메모리 해제
            del df
        except:
            continue
    
    # 스캔 종료 후 정리
    sys.stderr = orig_stderr
    f.close()
    gc.collect() # [오류 해결책] 메모리 찌꺼기 강제 청소

def bot_loop():
    send_ntfy("🚀 sm5 [위대한 항로] V2.3 불사신 버전 가동\n- 로그 끊김/멈춤 방지 로직 적용 완료")
    while True:
        try:
            weekend_review()
            check_heartbeat()
            start_hunting()
            time.sleep(300)
        except Exception as e:
            # 치명적 에러 시 재부팅 알림
            time.sleep(60)

if __name__ == "__main__":
    Thread(target=run_web_server, daemon=True).start()
    bot_loop()
