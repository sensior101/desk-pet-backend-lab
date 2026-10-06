import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("EUREKA_API_KEY")
BASE = "https://api.eureka.codes/flw-v1"

headers = {
    "x-api-key": KEY,
    "content-type": "application/json"
}

ITEM_ID = "1000010"

print("===== 업무 마감시간 연기 =====")

new_due_at = int((time.time() + 48 * 60 * 60) * 1000)

start = time.perf_counter()

response = requests.put(
    f"{BASE}/_api_/items/{ITEM_ID}",
    headers=headers,
    json={
        "dueAt": new_due_at
    },
    timeout=20
)

elapsed = time.perf_counter() - start

print("HTTP 상태:", response.status_code)
print("응답 시간:", round(elapsed, 3), "초")

if 200 <= response.status_code < 300:
    data = response.json()

    print("마감시간 연기 성공")
    print("itemId:", data.get("id"))
    print("업무 이름:", data.get("name"))
    print("변경된 dueAt:", data.get("dueAt"))

else:
    print("마감시간 연기 실패")
    print(response.text)