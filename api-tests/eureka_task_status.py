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

print("===== 업무 상태 확인 =====")

start = time.perf_counter()

response = requests.get(
    f"{BASE}/_api_/items/{ITEM_ID}/status",
    headers=headers,
    timeout=20
)

elapsed = time.perf_counter() - start

print("HTTP 상태:", response.status_code)
print("응답 시간:", round(elapsed, 3), "초")

if response.status_code == 200:
    data = response.json()

    print("itemId:", data.get("id"))
    print("업무 상태:", data.get("status"))
    print("전체 단계 수:", data.get("total"))
    print("완료 단계 수:", data.get("done"))

    if data.get("status") == "done":
        print("\n업무 완료 상태 검증 성공")
    else:
        print("\n예상 상태는 done인데 다른 값이 나왔습니다.")

else:
    print("상태 조회 실패")
    print(response.text)