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

print("===== 업무 전체 완료 =====")

start = time.perf_counter()

response = requests.post(
    f"{BASE}/_api_/items/{ITEM_ID}/complete",
    headers=headers,
    json={},
    timeout=20
)

elapsed = time.perf_counter() - start

print("HTTP 상태:", response.status_code)
print("응답 시간:", round(elapsed, 3), "초")

if 200 <= response.status_code < 300:
    print("업무 완료 처리 성공")

    data = response.json()

    print("itemId:", data.get("id"))
    print("업무 이름:", data.get("name"))

    print("\nStage 상태:")

    for stage in data.get("stage$$", []):
        print(
            "-",
            stage.get("name"),
            "상태:",
            stage.get("status")
        )

else:
    print("업무 완료 처리 실패")
    print(response.text)