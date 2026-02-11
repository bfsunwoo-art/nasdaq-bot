import requests

# 성민님의 최신 키 (스크린샷 확인 완료)
ALPACA_API_KEY = 'PKDAL2Z52D5YTI2V7N2TR2UXGO'
ALPACA_SECRET_KEY = '7odPStsrP7u931DN34UYsaYH1mJsUYZSo399uK3oHpHt'
# 모의투자 초기화 전용 주소
URL = 'https://paper-api.alpaca.markets/v2/account/configurations'

headers = {
    "APCA-API-KEY-ID": ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
}

# 알파카에게 잔고 리셋을 요청하는 마법의 명령어
# 주의: 이 기능은 일부 계정에서 작동 방식이 다를 수 있어 직접 리셋 API를 호출합니다.
reset_url = "https://paper-api.alpaca.markets/v2/account/reset"

print("💰 잔고 초기화 요청 중...")
response = requests.post(reset_url, headers=headers)

if response.status_code == 200:
    print("✅ 성공! 이제 대시보드를 새로고침하면 $100,000가 보일 겁니다.")
else:
    print(f"❌ 실패: {response.status_code}, 메시지: {response.text}")
        
