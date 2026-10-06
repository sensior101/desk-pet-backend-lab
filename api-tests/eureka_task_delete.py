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

ITEM_ID = "1000010"

print("===== 테스트 업무 삭제 =====")

start = time.perf_counter()

response = requests.delete(
    f"{BASE}/_api_/items/{ITEM_ID}",
    headers=headers,
    timeout=20
)

elapsed = time.perf_counter() - start

print("HTTP 상태:", response.status_code)
print("응답 시간:", round(elapsed, 3), "초")

if 200 <= response.status_code < 300:
    print("테스트 업무 삭제 성공")
else:
    print("테스트 업무 삭제 실패")
    print(response.text)