import yfinance as yf
import pandas as pd
import requests
import time
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home(): return "성민0106 폭풍의눈 시스템 가동중"

def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.daemon = True
    t.start()

NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=10)
    except: pass

# --- [성민0106 전용: 폭풍의 눈 후보군 150개 리스트] ---
WATCH_LIST = [
    "TTOO", "MULN", "GWAV", "FFIE", "BNSO", "SISI", "LUNR", "BBAI", "SOUN", "GNS",
    "RELI", "TCBP", "MGIH", "HUDI", "WISA", "VRAX", "PXMD", "IMPP", "OPOS", "AEI",
    "GRI", "MRAI", "TRKA", "EBET", "TGL", "IDEX", "XFOR", "AVPR", "LGMK", "SVRE",
    "TENX", "MGRM", "NVOS", "XIAO", "CDIO", "SNAL", "BSFC", "AMV", "ASTI", "MGIH",
    "BTTR", "EFTR", "CNEY", "HUBC", "ICU", "MTC", "BDRX", "BNRG", "AITX", "ABVC",
    "VREV", "FSRN", "PHUN", "MARK", "AEMD", "AKAN", "ASNS", "BGLC", "BSBK", "CBAS",
    "CDTG", "CEAD", "CLRO", "CPHI", "CTIB", "CXAI", "CYTO", "DLPN", "DTSS", "EDBL",
    "ENTX", "EVLO", "FEMY", "FRGT", "GDHG", "GGE", "GMVD", "GROM", "HEPA", "HOLO",
    "ICG", "IDAI", "IKT", "IMRN", "INBS", "ISPR", "ITP", "IVA", "IVCB", "JAN",
    "JZ", "KBNT", "KTRA", "KXIN", "LIFW", "LMFA", "LQR", "LYT", "MCOM", "MEGL",
    "METX", "MGIH", "MITQ", "MNY", "MRAI", "MSGM", "MSTB", "NAAS", "NBTX", "NCNC",
    "NCTY", "NEPT", "NKZN", "NNAV", "NTBP", "NUKK", "NXU", "OCG", "OMH", "OTRK",
    "OXBR", "PEGY", "PGAS", "PLUR", "PSHG", "PTGX", "PULM", "PWFL", "QRNR", "REVB",
    "RNLX", "SISI", "SLNH", "SNAL", "SNES", "STIX", "STRM", "SUMR", "SVMH", "SWIN",
    "SYTA", "TCON", "TENX", "TGL", "TOP", "TRKA", "UAVS", "UCAR", "UPXI", "VCNX",
    "VFS", "VISL", "VQS", "VRAR", "WAVD", "WNW", "XBP", "XHG", "YOSH", "ZAPP"
]

def scan_storm_eye():
    print(f"🔎 총 {len(WATCH_LIST)}개 종목 분석 시작...")
    for ticker in WATCH_LIST:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 1. 시가총액 필터 (약 1,000억 미만 = 7,500만 달러 이하)
            market_cap = info.get('marketCap', 0)
            if market_cap == 0 or market_cap > 80000000: # 8천만 달러 여유있게 설정
                continue

            df = stock.history(period="40d")
            if len(df) < 25: continue

            # 2. 거래량 분석 (최근 3일 내 최대 거래량이 20일 평균의 3배 이상)
            avg_vol_20 = df['Volume'].iloc[-21:-1].mean()
            max_vol_3d = df['Volume'].iloc[-3:].max()
            
            # 3. 횡보 조건 (20일 내 변동폭 15% 이내)
            high_20 = df['High'].iloc[-20:].max()
            low_20 = df['Low'].iloc[-20:].min()
            volatility = (high_20 - low_20) / low_20

            # 4. 정배열 초기/추세 확인 (현재가 > 20일선)
            ma20 = df['Close'].iloc[-20:].mean()
            current_price = df['Close'].iloc[-1]

            if max_vol_3d >= (avg_vol_20 * 3) and volatility <= 0.15 and current_price > ma20:
                msg = (f"🌪️ [폭풍의눈 포착!]\n"
                       f"종목: {ticker}\n"
                       f"시총: ${round(market_cap/1000000, 1)}M\n"
                       f"거래량: {round(max_vol_3d/avg_vol_20, 1)}배 폭증\n"
                       f"변동폭: {round(volatility*100, 1)}% (응축중)")
                send_ntfy(msg)
                print(f"✅ 포착: {ticker}")

        except:
            continue
    print("✨ 스캔 완료. 30분 후 재시작합니다.")

if __name__ == "__main__":
    keep_alive()
    while True:
        scan_storm_eye()
        time.sleep(1800) # 30분 대기








        
