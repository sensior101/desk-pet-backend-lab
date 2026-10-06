from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

# Timezone / Application bootstrap
# Mock 환경에서는 모든 시간 비교를 KST 기준으로 통일한다.
KST = timezone(timedelta(hours=9))

app = FastAPI(
    title="Desk Pet Mock Server",
    version="0.1.0",
    description=(
        "Desk Pet E2E 테스트용 Mock Server. "
        "LLM 분석, MCP 호출, Eureka Process 업무 관리, WebSocket proactive_alert를 로컬에서 흉내냅니다."
    ),
)


# Mock in-memory state
# 실제 아키텍처에서는 Reminder 관련 상태가
# ReminderRepositoryPort / DatabaseAdapter 경계를 통해 관리될 수 있다.
tasks: Dict[str, Dict[str, Any]] = {}
request_ids: set[str] = set()
connected_clients: Dict[str, List[WebSocket]] = {}
notified_task_ids: set[str] = set()

SCHEDULER_INTERVAL_SECONDS = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "5"))



# Request / Response models
# Mock API의 외부 계약을 정의한다.
# 실제 운영 코드에서는 Application DTO와 외부 Eureka DTO를
# 필요에 따라 분리할 수 있다.
class AnalyzeRequest(BaseModel):
    text: str = Field(..., examples=["내일 오후 3시까지 운영체제 과제 등록해줘"])
    user_id: str = "demo-user"
    current_time: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None


class AnalyzeResponse(BaseModel):
    intent: Literal["create_task", "list_tasks", "complete_task", "postpone_task", "unknown"]
    parameters: Dict[str, Any]
    required_tool: Optional[str] = None
    confidence: float = 1.0


class MCPCallRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "demo-user"
    tool_name: str
    operation: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TaskCreateRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "demo-user"
    title: str
    description: Optional[str] = None
    deadline: datetime
    priority: Literal["low", "medium", "high"] = "medium"
    alert_before_minutes: int = 60


class TaskUpdateRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    alert_before_minutes: Optional[int] = None


class StageStatusRequest(BaseModel):
    status: Literal["pending", "in_progress", "completed"]


class DebugAlertRequest(BaseModel):
    user_id: Optional[str] = None


# Shared helper functions
# Mock 내부 여러 API에서 공통으로 사용하는 보조 함수들이다.
def now_kst() -> datetime:
    return datetime.now(KST)


def normalize_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=KST)
    return dt.astimezone(KST)


def serialize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(task)
    for key in ("deadline", "created_at", "updated_at"):
        if isinstance(result.get(key), datetime):
            result[key] = result[key].isoformat()
    return result


def ensure_unique_request(request_id: str) -> None:
    if request_id in request_ids:
        raise HTTPException(status_code=409, detail="DUPLICATE_REQUEST_ID")
    request_ids.add(request_id)


def find_task(task_id: str) -> Dict[str, Any]:
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="TASK_NOT_FOUND")
    return task


async def push_event(user_id: str, payload: Dict[str, Any]) -> None:
    sockets = connected_clients.get(user_id, [])
    dead: List[WebSocket] = []

    for ws in sockets:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)

    if dead:
        connected_clients[user_id] = [ws for ws in sockets if ws not in dead]


# Health check
# Mock Server 실행 여부를 빠르게 확인하기 위한 단순 상태 확인 API.
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "deskpet-mock-server",
        "time": now_kst().isoformat(),
    }


# Mock Intent / LLM Orchestrator
@app.post("/api/llm/analyze", response_model=AnalyzeResponse)
async def analyze_user_request(req: AnalyzeRequest):
    text = req.text.strip()
    lowered = text.lower()

    if any(word in text for word in ["등록", "추가", "만들어", "일정 잡아"]):
        intent = "create_task"
        tool = "CreateSchedule"
    elif any(word in text for word in ["완료", "끝냈", "끝남", "다 했"]):
        intent = "complete_task"
        tool = "CompleteSchedule"
    elif any(word in text for word in ["미뤄", "연기", "변경"]):
        intent = "postpone_task"
        tool = "UpdateSchedule"
    elif any(word in text for word in ["조회", "보여", "뭐 있", "일정", "할 일"]):
        intent = "list_tasks"
        tool = "ListSchedule"
    else:
        intent = "unknown"
        tool = None

    # Mock이므로 복잡한 자연어 날짜 파싱은 하지 않고 원문을 파라미터로 넘긴다.
    return AnalyzeResponse(
        intent=intent,
        parameters={"raw_text": text, "context": req.context or {}},
        required_tool=tool,
        confidence=0.95 if intent != "unknown" else 0.35,
    )


# Simplified Backend Task API
# Mock 환경에서는 API endpoint가 인메모리 tasks 저장소를 직접 조작한다.
# TaskService는 Eureka의 URL, HTTP Method, DTO 구조를 직접 알지 않는다.
@app.post("/api/tasks", status_code=201)
async def create_task(req: TaskCreateRequest):
    ensure_unique_request(req.request_id)

    task_id = str(uuid.uuid4())
    deadline = normalize_dt(req.deadline)
    created_at = now_kst()

    task = {
        "id": task_id,
        "user_id": req.user_id,
        "title": req.title,
        "description": req.description,
        "deadline": deadline,
        "priority": req.priority,
        "alert_before_minutes": req.alert_before_minutes,
        "status": "pending",
        "stage_id": f"stage-{task_id[:8]}",
        "created_at": created_at,
        "updated_at": created_at,
    }
    tasks[task_id] = task

    return {
        "success": True,
        "task": serialize_task(task),
    }


@app.get("/api/tasks")
async def list_tasks(
    user_id: str = Query("demo-user"),
    status: Optional[str] = Query(None),
):
    result = [
        serialize_task(t)
        for t in tasks.values()
        if t["user_id"] == user_id and (status is None or t["status"] == status)
    ]
    result.sort(key=lambda x: x["deadline"])
    return {"success": True, "count": len(result), "tasks": result}


@app.get("/api/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    task = find_task(task_id)
    return {
        "success": True,
        "task_id": task_id,
        "status": task["status"],
        "deadline": task["deadline"].isoformat(),
    }


@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    task = find_task(task_id)
    task["status"] = "completed"
    task["updated_at"] = now_kst()
    return {"success": True, "task": serialize_task(task)}


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, req: TaskUpdateRequest):
    ensure_unique_request(req.request_id)
    task = find_task(task_id)

    update_data = req.model_dump(exclude_none=True)
    update_data.pop("request_id", None)

    if "deadline" in update_data:
        update_data["deadline"] = normalize_dt(update_data["deadline"])

    task.update(update_data)
    task["updated_at"] = now_kst()

    # 연기 후 다시 알림 받을 수 있도록 초기화
    notified_task_ids.discard(task_id)

    return {"success": True, "task": serialize_task(task)}


# Mock MCP Tool Gateway
@app.post("/api/mcp/call")
async def call_mcp_tool(req: MCPCallRequest):
    ensure_unique_request(req.request_id)

    operation = req.operation
    params = req.parameters

    if operation == "create_task":
        deadline_raw = params.get("deadline")
        title = params.get("title")
        if not title or not deadline_raw:
            raise HTTPException(status_code=422, detail="title and deadline are required")

        deadline = datetime.fromisoformat(str(deadline_raw).replace("Z", "+00:00"))
        task_id = str(uuid.uuid4())
        created_at = now_kst()

        task = {
            "id": task_id,
            "user_id": req.user_id,
            "title": title,
            "description": params.get("description"),
            "deadline": normalize_dt(deadline),
            "priority": params.get("priority", "medium"),
            "alert_before_minutes": int(params.get("alert_before_minutes", 60)),
            "status": "pending",
            "stage_id": f"stage-{task_id[:8]}",
            "created_at": created_at,
            "updated_at": created_at,
        }
        tasks[task_id] = task
        return {
            "success": True,
            "tool_name": req.tool_name,
            "operation": operation,
            "result": serialize_task(task),
        }

    if operation == "list_tasks":
        result = [
            serialize_task(t)
            for t in tasks.values()
            if t["user_id"] == req.user_id
        ]
        return {
            "success": True,
            "tool_name": req.tool_name,
            "operation": operation,
            "result": result,
        }

    if operation == "complete_task":
        task_id = params.get("task_id")
        if not task_id:
            raise HTTPException(status_code=422, detail="task_id is required")
        task = find_task(task_id)
        task["status"] = "completed"
        task["updated_at"] = now_kst()
        return {
            "success": True,
            "tool_name": req.tool_name,
            "operation": operation,
            "result": serialize_task(task),
        }

    if operation == "postpone_task":
        task_id = params.get("task_id")
        deadline_raw = params.get("deadline")
        if not task_id or not deadline_raw:
            raise HTTPException(status_code=422, detail="task_id and deadline are required")
        task = find_task(task_id)
        task["deadline"] = normalize_dt(
            datetime.fromisoformat(str(deadline_raw).replace("Z", "+00:00"))
        )
        task["updated_at"] = now_kst()
        notified_task_ids.discard(task_id)
        return {
            "success": True,
            "tool_name": req.tool_name,
            "operation": operation,
            "result": serialize_task(task),
        }

    raise HTTPException(status_code=400, detail="UNSUPPORTED_MCP_OPERATION")


# Mock Eureka Process API
# 실제 Eureka Process API의 endpoint 형태와 응답 흐름을
# 로컬에서 검증하기 위한 Mock interface다.
@app.post("/_api_/items/0/start", status_code=201)
async def eureka_start(req: TaskCreateRequest):
    # Mock 단독 사용을 위해 실제 task API와 동일한 저장소 사용
    return await create_task(req)


@app.get("/_api_/items/0/list")
async def eureka_list(
    sites: Optional[str] = None,
    detail: bool = True,
    user_id: str = "demo-user",
):
    _ = sites, detail
    return await list_tasks(user_id=user_id, status=None)


@app.post("/_api_/items/{item_id}/complete")
async def eureka_complete(item_id: str):
    return await complete_task(item_id)


@app.post("/_api_/stages/{stage_id}/status")
async def eureka_stage_status(stage_id: str, req: StageStatusRequest):
    for task in tasks.values():
        if task["stage_id"] == stage_id:
            task["status"] = req.status
            task["updated_at"] = now_kst()
            return {"success": True, "stage_id": stage_id, "status": req.status}
    raise HTTPException(status_code=404, detail="STAGE_NOT_FOUND")


@app.put("/_api_/items/{item_id}")
async def eureka_update(item_id: str, req: TaskUpdateRequest):
    return await update_task(item_id, req)


@app.get("/_api_/items/{item_id}/status")
async def eureka_status(item_id: str):
    return await get_task_status(item_id)


# WebSocket output channel
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    connected_clients.setdefault(user_id, []).append(websocket)

    await websocket.send_json({
        "event": "connected",
        "user_id": user_id,
        "message": "Desk Pet WebSocket connected",
        "timestamp": now_kst().isoformat(),
    })

    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_json({
                "event": "echo",
                "message": message,
                "timestamp": now_kst().isoformat(),
            })
    except WebSocketDisconnect:
        pass
    finally:
        sockets = connected_clients.get(user_id, [])
        connected_clients[user_id] = [ws for ws in sockets if ws is not websocket]

# Mock Scheduler / Reminder flow
# SchedulerAdapter 자체는 마감 판단 등의 비즈니스 규칙을 가지지 않는다.
async def scheduler_loop():
    while True:
        current = now_kst()

        for task_id, task in list(tasks.items()):
            if task["status"] == "completed":
                continue
            if task_id in notified_task_ids:
                continue

            deadline: datetime = task["deadline"]
            threshold = deadline - timedelta(minutes=task["alert_before_minutes"])

            if threshold <= current < deadline:
                payload = {
                    "event": "proactive_alert",
                    "type": "deadline_approaching",
                    "task_id": task_id,
                    "title": task["title"],
                    "deadline": deadline.isoformat(),
                    "alert_before_minutes": task["alert_before_minutes"],
                    "led": {
                        "color": "yellow",
                        "mode": "blink",
                    },
                    "lcd": {
                        "expression": "urgent",
                        "text": f"{task['title']} 마감 임박!",
                    },
                    "tts": f"{task['title']} 마감 시간이 얼마 남지 않았어요.",
                    "timestamp": current.isoformat(),
                }
                await push_event(task["user_id"], payload)
                notified_task_ids.add(task_id)

        await asyncio.sleep(SCHEDULER_INTERVAL_SECONDS)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduler_loop())


# Debug / presentation endpoints
@app.post("/api/debug/tasks/{task_id}/trigger-alert")
async def trigger_alert(task_id: str, req: DebugAlertRequest):
    task = find_task(task_id)
    user_id = req.user_id or task["user_id"]

    payload = {
        "event": "proactive_alert",
        "type": "debug",
        "task_id": task_id,
        "title": task["title"],
        "deadline": task["deadline"].isoformat(),
        "led": {"color": "yellow", "mode": "blink"},
        "lcd": {"expression": "urgent", "text": f"{task['title']} 마감 임박!"},
        "tts": f"{task['title']} 마감 시간이 얼마 남지 않았어요.",
        "timestamp": now_kst().isoformat(),
    }

    await push_event(user_id, payload)
    return {
        "success": True,
        "sent_to_user": user_id,
        "connected_clients": len(connected_clients.get(user_id, [])),
        "payload": payload,
    }


@app.delete("/api/debug/reset")
async def reset_mock():
    tasks.clear()
    request_ids.clear()
    notified_task_ids.clear()
    return {"success": True, "message": "mock data reset"}
