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

print("===== Process 목록 조회 =====")

start = time.perf_counter()

response = requests.get(
    f"{BASE}/_api_/processes/0/list?sites&detail=true&limit=50",
    headers=headers,
    timeout=20
)

elapsed = time.perf_counter() - start

print("HTTP 상태:", response.status_code)
print("응답 시간:", round(elapsed, 3), "초")

if response.status_code == 200:
    data = response.json()

    print("\n사용 가능한 Process:")

    for process in data.get("list", []):
        print(
            "이름:", process.get("name"),
            "ID:", process.get("id")
        )

else:
    print("Process 조회 실패")
    print(response.text)