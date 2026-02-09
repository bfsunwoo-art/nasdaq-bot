import yfinance as yf
import pandas as pd
import requests
import time
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home(): return "성민0106 폭풍의눈 v2.1 가동중"

def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.daemon = True
    t.start()

NTFY_URL = "https://ntfy.sh/sungmin_ssk_7"

def send_ntfy(message):
    try: requests.post(NTFY_URL, data=message.encode('utf-8'), timeout=10)
    except: pass

# [에러 종목 제거 완료] 깨끗한 135개 후보군
WATCH_LIST = [
    "TTOO", "GWAV", "BNSO", "SISI", "LUNR", "BBAI", "SOUN", "GNS",
    "RELI", "TCBP", "MGIH", "HUDI", "WISA", "VRAX", "PXMD", "IMPP", "AEI",
    "GRI", "MRAI", "TGL", "XFOR", "LGMK", "SVRE", "TENX", "MGRM", "NVOS", "CDIO", 
    "SNAL", "BSFC", "AMV", "ASTI", "BTTR", "EFTR", "CNEY", "HUBC", "ICU", "MTC", 
    "BDRX", "BNRG", "AITX", "ABVC", "FSRN", "PHUN", "MARK", "AEMD", "AKAN", "ASNS", 
    "BGLC", "BSBK", "CBAS", "CDTG", "CLRO", "CPHI", "CTIB", "CXAI", "CYTO", "DLPN", 
    "DTSS", "EDBL", "ENTX", "EVLO", "FEMY", "FRGT", "GDHG", "GGE", "GMVD", "GROM", 
    "HEPA", "HOLO", "ICG", "IDAI", "IKT", "IMRN", "INBS", "ISPR", "ITP", "IVA", 
    "IVCB", "JAN", "JZ", "KBNT", "KTRA", "KXIN", "LIFW", "LMFA", "LQR", "LYT", 
    "MCOM", "MEGL", "METX", "MITQ", "MNY", "MSGM", "MSTB", "NAAS", "NBTX", "NCNC", 
    "NCTY", "NTBP", "NUKK", "NXU", "OCG", "OMH", "OTRK", "OXBR", "PEGY", "PGAS", 
    "PLUR", "PSHG", "PTGX", "PULM", "PWFL", "RNLX", "SLNH", "SNES", "STIX", "SUMR", 
    "SVMH", "SWIN", "TOP", "UAVS", "UCAR", "UPXI", "VCNX", "VFS", "VISL", "VQS", 
    "VRAR", "XBP", "XHG"
]

def scan_storm_eye():
    print(f"\n🔎 [v2.1] 총 {len(WATCH_LIST)}개 종목 분석 시작...", flush=True)
    for ticker in WATCH_LIST:
        try:
            stock = yf.Ticker(ticker)
            market_cap = stock.info.get('marketCap', 0)
            
            # 시총 1000억 미만 필터 (약 8,000만 달러 이하)
            if market_cap == 0 or market_cap > 80000000:
                continue

            df = stock.history(period="40d")
            if len(df) < 25: continue

            # --- 조건 완화 섹션 ---
            # 1. 거래량: 20일 평균 대비 2배(200%)만 터져도 포착!
            avg_vol_20 = df['Volume'].iloc[-21:-1].mean()
            max_vol_3d = df['Volume'].iloc[-3:].max()
            is_volume_spike = max_vol_3d >= (avg_vol_20 * 2.0)
            
            # 2. 횡보: 20일 변동폭 22% 이내로 확장 (더 넓게 봄)
            high_20 = df['High'].iloc[-20:].max()
            low_20 = df['Low'].iloc[-20:].min()
            volatility = (high_20 - low_20) / low_20
            is_sideways = volatility <= 0.22

            # 3. 추세: 현재가가 20일선 근처면 인정
            ma20 = df['Close'].iloc[-20:].mean()
            current_price = df['Close'].iloc[-1]
            is_above_ma = current_price > (ma20 * 0.97) # 살짝 걸쳐있어도 OK

            if is_volume_spike and is_sideways and is_above_ma:
                msg = (f"🌪️ [폭풍의눈 v2.1 포착!]\n"
                       f"종목: {ticker}\n"
                       f"시총: ${round(market_cap/1000000, 1)}M\n"
                       f"거래량: {round(max_vol_3d/avg_vol_20, 1)}배\n"
                       f"변동폭: {round(volatility*100, 1)}% (박스권)")
                send_ntfy(msg)
                print(f"✅ 포착 성공: {ticker}", flush=True)

        except: continue
    print("✨ 스캔 완료. 30분 뒤에 다시 돌릴게요!", flush=True)

if __name__ == "__main__":
    keep_alive()
    while True:
        scan_storm_eye()
        time.sleep(1800)




        
