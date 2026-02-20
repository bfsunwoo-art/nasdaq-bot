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
import sys

# [수정 2] 생존 로직: 불필요한 경고 로그 차단 (Clean 환경 유지)
sys.stderr = open(os.devnull, 'w')

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

NY = timezone('America/New_York')
KST = timezone('Asia/Seoul')

def send_ntfy(msg):
    try: requests.post(NTFY_URL, data=msg.encode('utf-8'))
    except: pass

def log(msg):
    now_kst = datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now_kst}] {msg}", flush=True)

def auth_test():
    try:
        acc = api.get_account()
        if acc.status == 'ACTIVE':
            msg = f"✅ [sm7 V1.46 시작] 계좌 연결됨\nBP: ${float(acc.buying_power):,.2f}"
            send_ntfy(msg); log(msg); return True
    except Exception as e:
        send_ntfy(f"❌ API 연결 실패: {e}"); return False

# ==========================================
# 2. 시장 상태 및 방어막 (기존 유지)
# ==========================================
def get_market_status():
    now_ny = datetime.now(NY)
    now_kst = datetime.now(KST)
    clock = api.get_clock()
    if 8 <= now_kst.hour < 18: return "REST", False
    if clock.is_open:
        opened_at = clock.next_open.replace(tzinfo=NY) if not clock.is_open else clock.timestamp.replace(tzinfo=NY)
        if (now_ny - opened_at).total_seconds() < 1800: return "REGULAR_SHIELD", False
        return "REGULAR", True
    if 18 <= now_kst.hour < 23:
        if now_kst.hour == 18 and now_kst.minute < 20: return "PRE_MARKET_SHIELD", False
    return "EXTENDED", True

def check_buying_power_limit(priority):
    acc = api.get_account()
    equity = float(acc.equity)
    cash = float(acc.non_marginable_buying_power)
    used_ratio = (equity - cash) / equity
    if used_ratio > 0.70 and priority >= 3: return False
    return True

# ==========================================
# 3. 사냥 엔진 (P2 수치 수정 반영)
# ==========================================
def start_hunting(symbol):
    status, _ = get_market_status()
    is_extended = (status == "EXTENDED")

    if symbol in active_positions:
        try:
            trade = api.get_latest_trade(symbol)
            curr_price = trade.p
            pos = active_positions[symbol]
            if 'entry_ts' not in pos: pos['entry_ts'] = time.time()
            pos['highest_price'] = max(pos.get('highest_price', curr_price), curr_price)
            profit = (curr_price - pos['entry_price']) / pos['entry_price']
            drop_from_top = (pos['highest_price'] - curr_price) / pos['highest_price']
            elapsed = time.time() - pos['entry_ts']
            if elapsed > 1800 and profit < 0.005: 
                exit_trade(symbol, pos['qty'], profit, "타임컷(30m)", is_extended)
                return
            if profit <= -0.045:
                exit_trade(symbol, pos['qty'], profit, "손절(-4.5%)", is_extended)
            elif profit > 0.01 and drop_from_top >= 0.03:
                exit_trade(symbol, pos['qty'], profit, "추격익절", is_extended)
        except: pass
        return

    try:
        bars = api.get_bars(symbol, tradeapi.TimeFrame.Minute * 5, limit=50).df
        if bars.empty: return
        df = bars.copy()
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
        bb = ta.bbands(df['close'], length=20, std=2)
        df['bb_u'], df['bb_l'] = bb['BBU_20_2.0'], bb['BBL_20_2.0']
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=20)
        df['kc_u'] = df['close'].rolling(20).mean() + (df['atr'] * 1.5)
        df['kc_l'] = df['close'].rolling(20).mean() - (df['atr'] * 1.5)

        curr, prev = df.iloc[-1], df.iloc[-2]
        raw_vol_avg = df['volume'].rolling(window=20).mean().iloc[-2]
        vol_avg = (raw_vol_avg * 0.3) if is_extended else raw_vol_avg
        vol_avg = max(vol_avg, 1)

        priority = 0
        if curr['close'] > df['high'].iloc[-15:-1].max() and curr['RSI'] > prev['RSI'] and curr['close'] > prev['close'] * 1.05: priority = 1
        # [수정 1] P2 거래량 필터 성민님 요청 수치(0.6배) 반영
        elif curr['volume'] > (vol_avg * 0.6) and curr['RSI'] > prev['RSI'] and curr['close'] > prev['close'] * 1.05: priority = 2
        elif curr['close'] > df['high'].iloc[:5].max() and curr['volume'] > vol_avg * 1.1: priority = 3
        elif curr['close'] > (curr['VWAP'] * 1.0075): priority = 4
        elif curr['volume'] > (vol_avg * 2.0) and abs(curr['close'] - prev['close']) / prev['close'] < 0.01: priority = 5
        else:
            is_squeeze = (curr['bb_u'] < curr['kc_u']) and (curr['bb_l'] > curr['kc_l'])
            if is_squeeze and curr['volume'] > (vol_avg * 1.1): priority = 6

        if priority > 0:
            if not check_buying_power_limit(priority): return
            budget = 150 if priority <= 2 else 50
            qty = int(budget // curr['close'])
            if qty > 0:
                order_type = 'market'; limit_price = None
                if is_extended:
                    order_type = 'limit'; limit_price = round(curr['close'] * 1.01, 2)
                api.submit_order(symbol=symbol, qty=qty, side='buy', type=order_type, limit_price=limit_price, time_in_force='day' if is_extended else 'gtc', extended_hours=is_extended)
                active_positions[symbol] = {'entry_price': curr['close'], 'highest_price': curr['close'], 'qty': qty, 'tag': f'[P{priority}]', 'entry_ts': time.time()}
                send_ntfy(f"🎯 진입: {symbol} (P{priority}) | Type: {order_type}")
    except: pass

def exit_trade(symbol, qty, profit, reason, is_extended):
    try:
        trade = api.get_latest_trade(symbol)
        curr_price = trade.p
        order_type = 'market'; limit_price = None
        if is_extended:
            order_type = 'limit'; limit_price = round(curr_price * 0.99, 2)
        api.submit_order(symbol=symbol, qty=qty, side='sell', type=order_type, limit_price=limit_price, time_in_force='day' if is_extended else 'gtc', extended_hours=is_extended)
        send_ntfy(f"✅ 매도: {symbol}\n사유: {reason}\n익절: {profit*100:.2f}%")
        if symbol in active_positions: del active_positions[symbol]
    except: pass

# ==========================================
# 4. 시스템 관리 (기존 유지)
# ==========================================
def report_system():
    last_h = -1
    while True:
        now_kst = datetime.now(KST)
        if now_kst.hour != last_h:
            log(f"📡 하트비트 작동중 (누적 로그: {len(reject_log)}건)")
            send_ntfy(f"📡 [sm7 V1.46] {now_kst.strftime('%H:%M')} 가동중\n누적 로그: {len(reject_log)}건")
            last_h = now_kst.hour
            if now_kst.hour == 9:
                if reject_log:
                    send_ntfy(f"📋 [탈락 리포트]\n" + "\n".join(reject_log[-10:]))
                    reject_log.clear()
        time.sleep(60)

# ==========================================
# 5. 실행부 및 [수정 3] 402개 종목 리스트 완비
# ==========================================
app = Flask(__name__)
@app.route('/')
def health(): return "sm7 V1.46 Live", 200

BASE_SYMBOLS = ["ROLR","BNAI", "RXT", "BATL", "TMDE", "INDO", "SVRN", "DFLI", "JTAI", "GWAV", "LUNR", "BBAI", "SOUN", "GNS", "MGIH", "IMPP", "CING", "SNAL", "MRAI", "BRLS", "HUBC", "AGBA", "ICU", "TPST", "LGVN", "CNEY", "SCPX", "TCBP", "KITT", "RVSN", "SERV", "SMFL", "IVP", "WISA", "VHAI", "MGRM", "SPRC", "AENT", "AEI", "AEMD", "AEYE", "AEZS", "AFIB", "AIHS", "AIMD", "AITX", "AKAN", "AKBA", "AKTX", "ALBT", "ALDX", "ALOT", "ALPP", "ALRN", "ALVOP", "AMBO", "AMST", "ANIX", "ANY", "AOMR", "APDN", "APGN", "APLM", "APLT", "APTO", "APVO", "APWC", "AQB", "AQMS", "AQST", "ARAV", "ARBB", "ARBE", "ARBK", "ARCT", "ARDS", "ARDX", "AREB", "ARGX", "ARL", "ARMP", "ARQT", "ARSN", "ARTL", "ARTW", "ARVN", "ASNS", "ASPA", "ASPS", "ASRT", "ASRV", "ASST", "ASTI", "ASTR", "ASTS", "ASXC", "ATAI", "ATAK", "ATCG", "ATCP", "ATEC", "ATER", "ATGL", "ATNF", "ATNM", "ATNX", "ATOS", "ATPC", "ATRA", "ATRI", "ATRO", "ATXG", "AUBAP", "AUUD", "AVDL", "AVGR", "AVIR", "AVRO", "AVTX", "AVXL", "AWIN", "AWRE", "AXLA", "AXNX", "AXTI", "AYRO", "AYTU", "AZRE", "AZTR", "BANN", "BCAN", "BCDA", "BCEL", "BCOV", "BCSA", "BDRX", "BETS", "BFRI", "BGI", "BGLC", "BGM", "BHAT", "BIAF", "BIG", "BIOC", "BITF", "BKYI", "BLBX", "BLIN", "BLNK", "BLPH", "BLRX", "BLTE", "BLUE", "BMRA", "BNGO", "BNRG", "BNTC", "BOF", "BOSC", "BOXD", "BPT", "BRDS", "BRIB", "BRQS", "BRSH", "BRTX", "BSFC", "BSGM", "BTBD", "BTBT", "BTCS", "BTM", "BTOG", "BTTR", "BTTX", "BTU", "BURG", "BXRX", "BYFC", "BYRN", "BYSI", "BZFD", "CAPR", "CARV", "CASI", "CASS", "CATX", "CBAS", "CBIO", "CBMG", "CEMI", "CENN", "CENT", "CETY", "CEZA", "CFRX", "CGON", "CHNR", "CHRS", "CHSN", "CIDM", "CIFR", "CINC", "CIZN", "CJJD", "CKPT", "CLAR", "CLDI", "CLIR", "CLNE", "CLNN", "CLRB", "CLRO", "CLSD", "CLSK", "CLSN", "CLVR", "CLXT", "CMAX", "CMND", "CMRA", "CMRX", "CNET", "CNSP", "CNTX", "CNXA", "COCP", "CODX", "COGT", "COIN", "COMS", "CPHI", "CPIX", "CPOP", "CPTN", "CPX", "CRBP", "CRDL", "CRKN", "CRMD", "CRTD", "CRVO", "CRVS", "CSCW", "CSSEL", "CTIB", "CTIC", "CTLP", "CTMX", "CTNT", "CTRM", "CTSO", "CTXR", "CUEN", "CURI", "CVLB", "CVV", "CWBR", "CXAI", "CYAD", "CYAN", "CYBN", "CYCC", "CYCN", "CYN", "CYRN", "CYTO", "DARE", "DATS", "DBGI", "DCFC", "DCO", "DCTH", "DFFN", "DGHI", "DGLY", "DJV", "DLPN", "DMTK", "DNA", "DNMR", "DNUT", "DOMO", "DRMA", "DRRX", "DRTS", "DRUG", "DSCR", "DSGN", "DSKE", "DSSI", "DSX", "DTIL", "DTSS", "DVAX", "DXF", "DYAI", "DYNT", "DZZX", "EAAS", "EBIZ", "EBLU", "EBON", "ECOR", "EDBL", "EDSA", "EDTK", "EEIQ", "EFOI", "EGAN", "EGLX", "EGRX", "EHTH", "EIGI", "EKSO", "ELOX", "ELTK", "EMBK", "EMKR", "ENCP", "ENLV", "ENOB", "ENSC", "ENSV", "ENTG", "ENTX", "ENVB", "ENZC", "EOLS", "EOSE", "EPAY", "EPIX", "EPRX", "EQ", "EQOS", "ERAS", "ERC", "ERYP", "ESEA", "ESGC", "ESPR", "ETTX", "EVFM", "EVGN", "EVGO", "EVOK", "EVTV", "EXAI", "EXPR", "EYE", "EYEN", "EYPT", "FAMI", "FATE", "FBIO", "FBRX", "FCEL", "FCON", "FCRD", "FDMT", "FDP", "FENC", "FEXD", "FGEN", "FIXX", "FKWL", "FLGC", "FLGT", "FLUX", "FLXN", "FMTX", "FNCH", "FNHC", "FNKO", "FORW", "FOSL", "FOTU", "FOXW", "FRAF", "FRGT", "FRSX", "FSR", "FSRD", "FTFT", "FTII", "FTRE", "FTSV", "FTVI", "FUSB", "FUV", "FWBI", "FYBR", "GAIA", "GANL", "GAST", "GATO", "GAV", "GBCI", "GBLI", "GBTG", "GCBC", "GCI", "GCO", "GCT", "GDC", "GDHG", "GDNR", "GECC", "GEN", "GENE", "GENT", "GEOS", "GERN", "GES", "GFAI", "GFF", "GGE", "GHG", "GHSI", "GIC", "GIFP", "GIGM", "GIII", "GILT", "GIPR", "GIV", "GLAD", "GLBS", "GLG", "GLMD", "GLSI", "GLST", "GLTO", "GLUC", "GLUE", "GMDA", "GMGI", "GMVD", "GNE", "GNLN", "GNLX", "GNRC", "GNS", "GNTA", "GNTX", "GNUS", "GOEV", "GOGL", "GOL", "GOLD", "GOSS", "GOW", "GPAK", "GPAQ", "GREE", "GRI", "GRIN", "GRNA", "GRNQ", "GRNV", "GROW", "GRPN", "GRRR", "GRTS", "GRTX", "GRVY", "GSIT", "GSM", "GSUN", "GTBP", "GTCH", "GTH", "GTIM", "GTPB", "GTS", "GURE", "GVP", "GWRE", "GYRO", "HAPP", "HARP", "HASI", "HAYW", "HBCP", "HBIO", "HBMD", "HBP", "HCCH", "HCMA", "HCTI", "HDSN", "HEAR", "HEI", "HEN", "HEPA", "HHR", "HI", "HIBB", "HILS", "HIMX", "HIPO", "HIRE", "HISN", "HKIT", "HLBZ", "HLGN", "HLLY", "HLTH", "HMN", "HMPT", "HMST", "HNDL", "HNRG", "HOKU", "HOMB", "HOPE", "HOV", "HPK", "HROW", "HRT", "HRTG", "HRTX", "HRZN", "HSDT", "HSHP", "HSIC", "HSON", "HST", "HSTO", "HTBI", "HTCR", "HTGM", "HTLD", "HTOO", "HUBC", "HUIZ", "HURN", "HUSA", "HUT", "HVCW", "HVN", "HWHL", "HX", "HYMC", "HYPR", "HYRE", "HYW", "IART", "IBEX", "IBIO", "IBKR", "IBP", "ICAD", "ICCH", "ICCM", "ICLK", "ICMB", "ICPT", "ICU", "IDAI", "IDEX", "IDN", "IDRA", "IDW", "IDYA", "IEA", "IER", "IESC", "IEX", "IFBD", "IFRX", "IGC", "IGMS", "IIIV", "IIIVP", "IINN", "IIPR", "IKNA", "IKT", "ILAG", "ILPT", "IMAC", "IMCC", "IMCR", "IMGN", "IMMP", "IMMX", "IMNM", "IMPL", "IMPP", "IMRA", "IMRN", "IMUX", "IMVT", "IMXI", "INAB", "INBX", "INCR", "INCY", "INDO", "INFI", "INFY", "INGN", "INMB", "INMD", "INPX", "INSM", "INTA", "INTG", "INTT", "INTZ", "INUV", "INVE", "INVO", "INVV", "INZY", "IONM", "IONQ", "IONS", "IOR", "IOSP", "IOTS", "IPDN", "IPHA", "IPI", "IPW", "IPX", "IQ", "IRAD", "IRBT", "IRIX", "IRMD", "IRNT", "IROQ", "IRTC", "ISDR", "ISIG", "ISPC", "ISPO", "ISPR", "ISRG", "ISSC", "ISTR", "ITCI", "ITI", "ITOS", "ITP", "ITRG", "ITRM", "ITRN", "ITST", "ITUB", "IUX", "IVA", "IVC", "IVDA", "IVP", "IVR", "IVVD", "IXHL", "IZM", "JAGX", "JAKK", "JAMF", "JAN", "JZ", "KALA", "KALV", "KAVL", "KBEW", "KBNT", "KDNY", "KEAR", "KELYB", "KERN", "KFFB", "KFS", "KID", "KILI", "KIN", "KIRK", "KITT", "KLR", "KLU", "KMDN", "KMPH", "KNDI", "KNSA", "KNTK", "KOD", "KOPN", "KORE", "KORR", "KOSS", "KPON", "KPRX", "KRBP", "KRKR", "KRMD", "KRNY", "KROS", "KRT", "KRTX", "KRYS", "KSCP", "KSPN", "KTRA", "KTSP", "KURA", "KVSA", "KW", "KXIN", "KYMR", "KZIA", "LABP", "LAC", "LAES", "LAKE", "LAMR", "LARK", "LASR", "LAZR", "LBAI", "LBC", "LCI", "LCLP", "LCNB", "LDWY", "LE", "LEAF", "LEGN", "LEJU", "LEN", "LENS", "LEXX", "LFCR", "LFMD", "LFST", "LFVN", "LGI", "LGL", "LGND", "LGVC", "LGVN", "LHCG", "LI", "LIDR", "LIQT", "LITM", "LIVN", "LL", "LLAP", "LLNW", "LMDX", "LMFA", "LMNL", "LMNR", "LMT", "LNC", "LND", "LNDC", "LNW", "LOAN", "LOB", "LOBO", "LODL", "LOPE", "LOPR", "LOV", "LOVE", "LPCN", "LPL", "LPRO", "LPTX", "LPTH", "LQDA", "LRHC", "LRMR", "LSEA", "LSPD", "LSTA", "LTBR", "LTRN", "LTRPB", "LTRX", "LU", "LUMO", "LUNA", "LUNR", "LVO", "LVRO", "LVTX", "LW", "LX", "LXEH", "LYEL", "LYRA", "LYT", "LZM", "MACK", "MAG", "MAIA", "MANU", "MARA", "MARK", "MASI", "MATW", "MAV", "MAXN", "MBRX", "MBSC", "MCB", "MCHX", "MCI", "MCRI", "MDJH", "MDNA", "MDVL", "MDWD", "MDXG", "ME", "MEDS", "MEGL", "MELI", "MEP", "MERC", "MESO", "METX", "MFA", "MGEE", "MGIH", "MGLD", "MGNI", "MGOL", "MGPI", "MGRM", "MGU", "MGX", "MHLD", "MIGI", "MIRM", "MIRV", "MIST", "MITK", "MITQ", "MKD", "MKL", "MLAC", "MLCO", "MLNK", "MLP", "MLTX", "MMAT", "MMI", "MMMB", "MMTEC", "MMV", "MNAF", "MNDO", "MNKD", "MNMD", "MNPR", "MNRO", "MNTS", "MNTV", "MOXC", "MPAA", "MPB", "MPLN", "MPW", "MQ", "MRAI", "MRAM", "MRBK", "MRC", "MRCC", "MRIN", "MRKR", "MRNA", "MRNS", "MRSN", "MRTX", "MRUS", "MRVI", "MSB", "MSGM", "MSON", "MSTR", "MTBC", "MTC", "MTCH", "MTCR", "MTEM", "MTNB", "MTP", "MTR", "MTRX", "MTTR", "MTVV", "MULN", "MVLA", "MVNC", "MVST", "MVT", "MWG", "MXCT", "MYMD", "MYNZ", "MYO", "MYPS", "MYSZ", "NAAS", "NAMS", "NANO", "NAOV", "NARI", "NAT", "NATH", "NAUT", "NAVB", "NBEV", "NBIX", "NBN", "NBRV", "NBTB", "NCNA", "NCPL", "NCTY", "NDRA", "NEGG", "NEO", "NEON", "NEOV", "NEPH", "NET", "NETE", "NEV", "NEWT", "NEXI", "NEXT", "NFBK", "NFE", "NFLX", "NG", "NGL", "NGM", "NGS", "NH", "NHI", "NICK", "NILE", "NINE", "NIO", "NITO", "NKTR", "NKTX", "NLY", "NM", "NMFC", "NMHI", "NMIH", "NMM", "NMRK", "NMRX", "NMT", "NNDM", "NNI", "NOAH", "NOK", "NOMD", "NOTV", "NOV", "NOVA", "NOW", "NR", "NRBO", "NRC", "NRDY", "NRG", "NRGV", "NRIM", "NRIX", "NRXP", "NS", "NSAS", "NSIT", "NSP", "NSTG", "NSTR", "NSYS", "NTE", "NTIC", "NTLA", "NTNX", "NTP", "NTRB", "NTRS", "NTST", "NTZ", "NU", "NUE", "NURO", "NUS", "NUVA", "NUZE", "NVAC", "NVAX", "NVCN", "NVCT", "NVEE", "NVIV", "NVNO", "NVOS", "NVVE", "NWBO", "NXGL", "NXPL", "NXPR", "NXST", "NXTD", "NXTP", "NYCB", "NYMT", "OB", "OBAS", "OBELF", "OCEA", "OCGN", "OCUL", "OCUP", "ODD", "ODP", "OEG", "OESX", "OIG", "OII", "OIS", "OKTA", "OLB", "OLED", "OLLI", "OLMA", "OLN", "OLP", "OM", "OMAB", "OMER", "OMGA", "OMP", "ON", "ONCO", "ONCS", "ONCT", "ONDS", "ONE", "ONEM", "ONL", "ONMD", "ONTF", "ONVO", "OOMA", "OP", "OPAD", "OPCH", "OPEN", "OPGN", "OPK", "OPRA", "OPRT", "OPRX", "OPT", "OPTT", "OPY", "ORAN", "ORBC", "ORCC", "ORCH", "ORGO", "ORGS", "ORIC", "ORMP", "ORN", "ORPH", "ORTX", "OSBC", "OSG", "OSIS", "OSPN", "OSS", "OST", "OSTK", "OTEC", "OTEL", "OTIC", "OTLK", "OTLY", "OTRK", "OTTR", "OUST", "OVV", "OXAC", "OXBR", "OXLC", "OXSQ", "OXY", "OYST", "OZ", "OZK", "PAAS", "PACB", "PAG", "PAGP", "PAGS", "PAHC", "PANL", "PANW", "PAR", "PARA", "PARP", "PASH", "PATK", "PATL", "PAVM", "PAY", "PAYO", "PAYS", "PB", "PBA", "PBBK", "PBFS", "PBH", "PBI", "PBIP", "PBLA", "PBPB", "PBT", "PBTS", "PBYI", "PCAR", "PCB", "PCH", "PCI", "PCN", "PCOR", "PCQ", "PCRX", "PCT", "PD", "PDC", "PDCE", "PDD", "PDLB", "PDOT", "PDSB", "PDT", "PEB", "PECO", "PEG", "PEGR", "PEGY", "PENN", "PEO", "PEPG", "PERI", "PETQ", "PETS", "PETZ", "PEV", "PFBC", "PFE", "PFG", "PFGC", "PFH", "PFI", "PFIS", "PFL", "PFLT", "PFMT", "PFN", "PFSW", "PGY", "PHAR", "PHAS", "PHAT", "PHCF", "PHG", "PHGE", "PHIO", "PHR", "PHT", "PHUN", "PHVS", "PHX", "PI", "PICO", "PID", "PII", "PINS", "PIPR", "PIRS", "PIXY", "PJH", "PK", "PKE", "PKG", "PKOH", "PLAB", "PLAG", "PLAN", "PLAY", "PLBY", "PLG", "PLIN", "PLMR", "PLOW", "PLPH", "PLRX", "PLSE", "PLTK", "PLTR", "PLUG", "PLUR", "PLUS", "PLXP", "PLXS", "PLYA", "PMD", "PMDY", "PMT", "PNC", "PNFP", "PNNT", "PNT", "PNTG", "PNW", "PODD", "POL", "POOL", "POR", "POSH", "POST", "POWI", "POWL", "POWW", "PPD", "PPIH", "PPL", "PPSI", "PPU", "PQEFF", "PRAA", "PRCH", "PRDS", "PRE", "PRFT", "PRFX", "PRG", "PRGO", "PRGS", "PRHL", "PRI", "PRIM", "PRLD", "PRO", "PROC", "PROF", "PROG", "PRPH", "PRPL", "PRPO", "PRQR", "PRSO", "PRT", "PRTA", "PRTG", "PRTH", "PRTK", "PRTS", "PRTY", "PRU", "PRVB", "PRVL", "PSMT", "PSNL", "PSTI", "PSTX", "PSX", "PT", "PTC", "PTEN", "PTGX", "PTH", "PTIX", "PTLO", "PTMN", "PTN", "PTNR", "PTON", "PTPI", "PTPI", "PTRA", "PTRS", "PTVE", "PUBM", "PUK", "PULM", "PVBC", "PVH", "PW", "PWFL", "PWR", "PWSC", "PX", "PXLW", "PYCR", "PYPD", "PYPL", "PYS", "PYT", "PZZA", "QCOM", "QCRH", "QD", "QDEL", "QES", "QFIN", "QGEN", "QNCX", "QNST", "QNRX", "QPT", "QRHC", "QRTEA", "QRVO", "QS", "QSI", "QSR", "QTEK", "QTNT", "QTRX", "QTT", "QTWO", "QUAD", "QUBT", "QUIK", "QUOT", "QVCC", "QYLD", "RADA", "RADI", "RADL", "RAIL", "RAMP", "RANI", "RARE", "RAVN", "RAYA", "RBC", "RBCAA", "RBKB", "RBT", "RC", "RCAT", "RCEL", "RCH", "RCI", "RCKT", "RCL", "RCM", "RCMQ", "RCON", "RCRT", "RCS", "RCUS", "RDDT", "RDHL", "RDIB", "RDNT", "RDUS", "RDVT", "RDY", "REAL", "REED", "REKR", "RELY", "RENB", "RENT", "REPH", "REPL", "REPX", "RETO", "REV", "REVB", "REVG", "REVO", "REX", "REXR", "REXX", "RF", "RFIL", "RFL", "RGCO", "RGEN", "RGLS", "RGNX", "RGP", "RGR", "RGS", "RGTI", "RH", "RHE", "RIBT", "RIG", "RIGL", "RILY", "RING", "RIOT", "RIVN", "RJA", "RKDA", "RKLB", "RKT", "RKTA", "RLAY", "RLJ", "RLMD", "RLTY", "RM", "RMBS", "RMCF", "Rmed", "RMGB", "RMNI", "RMTI", "RNA", "RNAC", "RNGR", "RNN", "RNR", "RNW", "RNXT", "ROAD", "ROAN", "ROBT", "ROCK", "ROIC", "ROIV", "ROKU", "ROLR", "ROMI", "RONI", "ROOF", "ROOT", "ROST", "ROVR", "RPT", "RPTX", "RPY", "RRBI", "RRC", "RRGB", "RRR", "RS", "RSKD", "RSLS", "RSSS", "RSVR", "RTX", "RUBY", "RUN", "RUSHA", "RUSHB", "RUTH", "RVLP", "RVMD", "RVNC", "RVP", "RVPH", "RVSN", "RVW", "RWAY", "RWE", "RWLK", "RXDX", "RXRA", "RXRX", "RXT", "RYAAY", "RYAM", "RYAN", "RYDE", "RYTM", "SABR", "SAFE", "SAFT", "SAGE", "SAI", "SAIA", "SAIC", "SAIT", "SAL", "SANA", "SANM", "SANY", "SAP", "SAR", "SASI", "SAT", "SAVA", "SAVE", "SB", "SBAC", "SBAY", "SBBC", "SBBX", "SBCF", "SBET", "SBGI", "SBH", "SBNY", "SBOW", "SBR", "SBRA", "SBSI", "SBT", "SBUX", "SC", "SCCO", "SCDL", "SCE", "SCHL", "SCHN", "SCHW", "SCI", "SCKT", "SCL", "SCM", "SCNI", "SCOR", "SCPH", "SCPL", "SCPX", "SCSC", "SCU", "SCVL", "SCWX", "SCX", "SD", "SDC", "SDG", "SDGR", "SDI", "SDIG", "SDPI", "SE", "SEAC", "SEAS", "SEAT", "SECO", "SEDG", "SEE", "SEED", "SEEL", "SEER", "SEIC", "SELB", "SELF", "SELO", "SEM", "SEMR", "SENEA", "SENEB", "SENS", "SENT", "SERA", "SERV", "SES", "SESN", "SF", "SFE", "SFIX", "SFM", "SFNC", "SFT", "SG", "SGC", "SGHT", "SGLB", "SGMA", "SGN", "SGNA", "SGOC", "SGRP", "SGTX", "SHAK", "SHC", "SHCR", "SHEN", "SHIP", "SHLS", "SHLX", "SHOO", "SHOP", "SHPH", "SHSP", "SI", "SIBN", "SIEB", "SIEN", "SIFY", "SIG", "SIGA", "SINT", "SINTX", "SIRI", "SITM", "SIVB", "SIX", "SJ", "SJI", "SKLZ", "SKX", "SKYE", "SKYT", "SLAB", "SLAM", "SLB", "SLDB", "SLGC", "SLGG", "SLGL", "SLGN", "SLNG", "SLNO", "SLP", "SLQT", "SLRX", "SLS", "SM", "SMAR", "SMBC", "SMBK", "SMCI", "SMFL", "SMFR", "SMHI", "SMLR", "SMLT", "SMMT", "SMPL", "SMR", "SMTC", "SNA", "SNAL", "SNBR", "SNCE", "SND", "SNDL", "SNDR", "SNES", "SNFCA", "SNN", "SNPO", "SNPX", "SNSE", "SNV", "SNX", "SNY", "SOFI", "SOL", "SOLO", "SONO", "SONS", "SOR", "SOUN", "SOVO", "SP", "SPAR", "SPB", "SPCE", "SPFI", "SPG", "SPH", "SPIR", "SPI", "SPK", "SPKL", "SPNE", "SPNS", "SPOK", "SPOT", "SPRB", "SPRC", "SPRE", "SPRO", "SPRT", "SPSC", "SPTK", "SPTN", "SPWH", "SPWR", "SQ", "SQFT", "SQSP", "SQZ", "SR", "SRAD", "SRAX", "SRCE", "SRDX", "SRE", "SRET", "SRG", "SRGA", "SRI", "SRK", "SRL", "SRLP", "SRNE", "SRPT", "SRRK", "SRSA", "SRT", "SRTS", "SRV", "SRVN", "SSB", "SSBI", "SSKN", "SSNC", "SSNT", "SSRM", "SST", "SSTK", "SSTR", "STA", "STAA", "STAB", "STAF", "STAG", "STAR", "STAT", "STBA", "STCN", "STDK", "STE", "STEM", "STEP", "STG", "STIM", "STIX", "STK", "STKL", "STKS", "STKT", "STL", "STLD", "STLY", "STMP", "STNE", "STNG", "STOK", "STON", "STOR", "STRA", "STRC", "STRE", "STRM", "STRO", "STRR", "STRS", "STRT", "STRU", "STRY", "STSA", "STTK", "STX", "STXS", "STZ", "SU", "SUI", "SUM", "SUN", "SUNL", "SUNP", "SUNW", "SUP", "SUPV", "SURF", "SUSA", "SUSB", "SUT", "SUVN", "SV", "SVB", "SVFA", "SVFD", "SVRA", "SVRN", "SVVC", "SWAG", "SWAV", "SWBI", "SWCH", "SWI", "SWIR", "SWK", "SWKH", "SWKS", "SWM", "SWN", "SWTX", "SWVL", "SXC", "SXI", "SXL", "SXTC", "SY", "SYBX", "SYF", "SYNA", "SYNH", "SYRS", "SYT", "SYTA", "SZ", "TAL", "TALS", "TALO", "TAM", "TAP", "TARA", "TARS", "TASI", "TATT", "TAV", "TAYD", "TBB", "TBC", "TBI", "TBK", "TBLA", "TBLT", "TBNK", "TBPH", "TBT", "TC", "TCBC", "TCBI", "TCBK", "TCBP", "TCBS", "TCBX", "TCDA", "TCF", "TCFC", "TCI", "TCMD", "TCN", "TCON", "TCRR", "TCRT", "TCS", "TCT", "TDUP", "TDW", "TEAF", "TEAM", "TEB", "TECH", "TEDU", "TELL", "TENB", "TER", "TERP", "TETU", "TFFP", "TFI", "TFinish", "TFX", "TGB", "TGC", "TGEN", "TGH", "TGI", "TGL", "TGLS", "TGNA", "TGTX", "TH", "THAR", "THBR", "THC", "THCH", "THFF", "THMO", "THO", "THRD", "THRY", "THTX", "THW", "TIG", "TIGR", "TILE", "TILS", "TILT", "TIMB", "TIO", "TIP", "TIPT", "TIRX", "TITN", "TIV", "TK", "TKAT", "TKC", "TKLF", "TKR", "TLRY", "TLSA", "TM", "TMBR", "TMCI", "TMDE", "TMDX", "TME", "TMFC", "TMHC", "TMKR", "TMO", "TMP", "TMPL", "TMPO", "TMQ", "TMT", "TMUS", "TNAV", "TNXP", "TNX", "TOL", "TOP", "TOUR", "TPB", "TPC", "TPII", "TPL", "TPRE", "TPST", "TPTX", "TPVG", "TRAB", "TRC", "TRCA", "TRCH", "TRDA", "TRDE", "TREE", "TREX", "TRHC", "TRI", "TRIB", "TRIN", "TRIP", "TRIT", "TRKA", "TRMD", "TRML", "TRMT", "TRN", "TRNS", "TRNX", "TRON", "TROW", "TRP", "TRPX", "TRQ", "TRST", "TRT", "TRTX", "TRU", "TRUE", "TRUP", "TRV", "TRVI", "TRVN", "TRX", "TSAT", "TSBK", "TSC", "TSCO", "TSEM", "TSHA", "TSL", "TSLA", "TSLX", "TSM", "TSN", "TSOI", "TSP", "TSRI", "TSS", "TSSI", "TST", "TSTR", "TSVT", "TTD", "TTEC", "TTGT", "TTI", "TTMI", "TTNP", "TTOO", "TTPH", "TUP", "TURB", "TURN", "TUSK", "TVTX", "TVTY", "TW", "TWAY", "TWIN", "TWLO", "TWNI", "TWNK", "TWO", "TWOU", "TWST", "TWTR", "TXG", "TXMD", "TXN", "TXRH", "TYRA", "TZOO", "U", "UAMY", "UBER", "UBFO", "UBX", "UCBI", "UCER", "UCFC", "UCL", "UCON", "UCTT", "UDMY", "UE", "UEC", "UEIC", "UFCS", "UFPT", "UHAL", "UHS", "UI", "UIS", "ULCC", "ULLU", "ULTR", "UMAC", "UMBF", "UMH", "UMX", "UNAM", "UNB", "UNCT", "UNFI", "UNF", "UNIT", "UNP", "UNRV", "UNTY", "UPC", "UPH", "UPLD", "UPST", "UPWK", "URBN", "URG", "URGN", "URI", "URM", "UROV", "URRE", "URSN", "USA", "USAK", "USAS", "USB", "USBC", "USEG", "USFD", "USG", "USIO", "USLM", "USNA", "USPH", "UST", "UTHR", "UTI", "UTL", "UTMD", "UTSI", "UUUU", "UVE", "UVSP", "UVV", "UXIN", "V", "VAC", "VACC", "VALU", "VANI", "VAQC", "VATE", "VAY", "VBC", "VBFC", "VBIT", "VBNK", "VBTX", "VC", "VCEL", "VCI", "VCNX", "VCO", "VCOT", "VCTR", "VCYT", "VEC", "VECO", "VEEV", "VEL", "VELO", "Venty", "VERA", "VERB", "VERI", "VERO", "VERU", "VERV", "VERY", "VET", "VFC", "VFF", "VFRM", "VG", "VGAS", "VGCX", "VGFC", "VGI", "VGLT", "VGSH", "VGR", "VHC", "VHI", "VHAI", "VIA", "VIAC", "VIAV", "VIBN", "VICI", "VICR", "VID", "VIE", "VIG", "VIGI", "VILL", "VINC", "VINE", "VINP", "VIPS", "VIR", "VIRC", "VIRI", "VIRT", "VIS", "VISL", "VIST", "VKTX", "VLDR", "VLGEA", "VLN", "VLNS", "VLO", "VLP", "VLRS", "VLRX", "VLY", "VMC", "VMEO", "VMET", "VMI", "VMNT", "VMO", "VMP", "VNDA", "VNE", "VNET", "VNOM", "VNRX", "VNS", "VNT", "VNTR", "VNUE", "VOC", "VOLT", "VOXX", "VP", "VPG", "VPRB", "VPU", "VPV", "VRA", "VRAX", "VRAY", "VRCA", "VRE", "VREO", "VRM", "VRME", "VRN", "VRNS", "VRP", "VRRM", "VRSK", "VRSN", "VRT", "VRTU", "VRTX", "VRTZ", "VRTV", "VRYY", "VSAT", "VSCO", "VSEC", "VSH", "VSI", "VSL", "VSM", "VSS", "VST", "VSTA", "VSTM", "VSTO", "VSTR", "VTGN", "VTI", "VTNR", "VTOL", "VTR", "VTRU", "VTSI", "VTV", "VTVT", "VTY", "VUZI", "VVI", "VVNT", "VVO", "VVOS", "VVR", "VVV", "VVX", "VWTR", "VXRT", "VYGR", "VYNE", "VYNT", "VZ", "W", "WAB", "WABC", "WAFD", "WAFU", "WAGE", "WAL", "WALA", "WARR", "WASH", "WAT", "WATT", "WAVE", "WAVS", "WB", "WBA", "WBD", "WBS", "WBX", "WCC", "WCP", "WDI", "WDS", "WDSC", "WE", "WEAV", "WEC", "WEN", "WERN", "WES", "WETG", "WEX", "WEYS", "WF", "WFC", "WFG", "WGO", "WH", "WHG", "WHLM", "WHLR", "WHR", "WIFI", "WILD", "WING", "WINT", "WISA", "WISH", "WIT", "WIW", "WIX", "WK", "WKHS", "WKME", "WLFC", "WLK", "WLKP", "WLL", "WLMS", "WM", "WMB", "WMC", "WMG", "WMK", "WMPN", "WMS", "WMT", "WNC", "WNEB", "WNS", "WNW", "WOLF", "WOOF", "WOR", "WORK", "WPP", "WPRT", "WRE", "WRES", "WRK", "WRLD", "WRN", "WRT", "WSBC", "WSC", "WSFS", "WSG", "WSM", "WSO", "WSR", "WST", "WSTG", "WT", "WTER", "WTFC", "WTI", "WTM", "WTRG", "WTS", "WTT", "WTTR", "WTW", "WU", "WULF", "WVE", "WVFC", "WVVI", "WW", "WWD", "WWR", "WWW", "WY", "WYNN", "WYY", "X", "XAIR", "XBI", "XBIO", "XBIT", "XBPH", "XCUR", "XEL", "XELA", "XENE", "XERS", "XFIN", "XFOR", "XGN", "XHR", "XOM", "XOMA", "XOS", "XP", "XPEL", "XPER", "XPL", "XPO", "XPOF", "XPP", "XPRO", "XRAY", "XRTX", "XSPA", "XTAG", "XTI", "XTNT", "XTR", "XTRA", "XTV", "XTW", "XUN", "XXII", "XYL", "XYO", "YALA", "YAYO", "YELP", "YETI", "YEXT", "YI", "YIN", "YMAB", "YMTX", "YNDX", "YORW", "YOTR", "YPF", "YQ", "YRD", "YSG", "YTRA", "YUM", "YUMA", "YUMC", "YVR", "YXX", "Z", "ZAL", "ZANL", "ZAPP", "ZBH", "ZBRA", "ZCMD", "ZD", "ZEAL", "ZENV", "ZEPP", "ZEUS", "ZFOX", "ZGN", "ZGYO", "ZI", "ZIM", "ZIMV", "ZING", "ZION", "ZIONP", "ZIP", "ZIXI", "ZLAB", "ZM", "ZMD", "ZNTL", "ZOM", "ZOP", "ZORE", "ZOS", "ZOV", "ZPTA", "ZR", "ZRO", "ZSAN", "ZS", "ZST", "ZTE", "ZTO", "ZTR", "ZTS", "ZUMZ", "ZUO", "ZURA", "ZVIA", "ZVO", "ZVSA", "ZWS", "ZY", "ZYME", "ZYNE", "ZYXI" ]
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
                log(f"Main Loop Error: {e}"); time.sleep(10)
