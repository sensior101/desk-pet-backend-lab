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

print("===== 업무 목록 조회 =====")

start = time.perf_counter()

response = requests.get(
    f"{BASE}/_api_/items/0/list?sites&detail=true&limit=100",
    headers=headers,
    timeout=20
)

elapsed = time.perf_counter() - start

print("HTTP 상태:", response.status_code)
print("응답 시간:", round(elapsed, 3), "초")

if response.status_code == 200:

    data = response.json()

    found = None

    for item in data.get("list", []):
        if str(item.get("id")) == ITEM_ID:
            found = item
            break

    if found:
        print("\n방금 등록한 업무 조회 성공")
        print("itemId:", found.get("id"))
        print("업무 이름:", found.get("name"))
        print("우선순위:", found.get("priority"))
        print("마감시간:", found.get("dueAt"))

        print("\nStage 목록:")

        for stage in found.get("stage$$", []):
            print(
                "-",
                stage.get("name"),
                "상태:",
                stage.get("status")
            )

    else:
        print("\nitemId 1000010을 찾지 못했습니다.")

else:
    print("조회 실패:")
    print(response.text)