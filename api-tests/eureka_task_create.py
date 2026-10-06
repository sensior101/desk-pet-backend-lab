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

PROCESS_ID = "general-work-v1@10204"

print("===== 테스트 업무 등록 =====")

# 현재 시각 기준 24시간 후를 마감시간으로 설정
due_at = int((time.time() + 24 * 60 * 60) * 1000)

start = time.perf_counter()

response = requests.post(
    f"{BASE}/_api_/items/0/start",
    headers=headers,
    json={
        "processId": PROCESS_ID,
        "name": "데스크 펫 Eureka 연동 테스트",
        "dueAt": due_at,
        "priority": "high"
    },
    timeout=20
)

elapsed = time.perf_counter() - start

print("HTTP 상태:", response.status_code)
print("응답 시간:", round(elapsed, 3), "초")

if 200 <= response.status_code < 300:
    data = response.json()

    item_id = data.get("id")
    stage_ids = data.get("stageIds", [])

    print("업무 등록 성공")
    print("업무 이름:", data.get("name"))
    print("itemId:", item_id)
    print("stageIds:", stage_ids)

else:
    print("업무 등록 실패")
    print(response.text)