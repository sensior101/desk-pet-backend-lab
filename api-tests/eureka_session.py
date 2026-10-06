import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("EUREKA_API_KEY")
BASE = "https://api.eureka.codes/flw-v1"

headers = {
    "x-api-key": KEY
}

print("===== Session 확인 =====")

start = time.perf_counter()

response = requests.get(
    f"{BASE}/_api_/session",
    headers=headers,
    timeout=20
)

elapsed = time.perf_counter() - start

print("HTTP 상태:", response.status_code)
print("응답 시간:", round(elapsed, 3), "초")

if response.status_code == 200:
    data = response.json()

    print("sid:", data.get("sid"))
    print("uid:", data.get("uid"))
    print("인증 성공")

else:
    print("인증 실패")
    print(response.text)