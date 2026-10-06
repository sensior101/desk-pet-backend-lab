# Desk Pet Mock Server

실제 Eureka Process 및 LLM/MCP 연동 전에 Desk Pet의 핵심 요청/응답 계약과 E2E 흐름을 검증하기 위한 FastAPI Mock Server입니다.

이 Mock Server는 실제 운영 백엔드 구조를 완전히 구현하는 목적이 아니라,
업무 등록·조회·상태 변경·마감 알림·WebSocket 전달 흐름을 빠르게 검증하기 위한 테스트 환경입니다.

---

## 포함 기능

- `POST /api/llm/analyze`
  - 경량 Intent Model 이후 단계의 Intent/LLM Orchestrator 동작을 Mock으로 흉내냄
  - 사용자 문장을 받아 `intent + parameters + required_tool` 형태로 정규화

- `POST /api/mcp/call`
  - MCP tool 호출 흐름 Mock

- 업무 API
  - `POST /api/tasks`
  - `GET /api/tasks`
  - `POST /api/tasks/{id}/complete`
  - `GET /api/tasks/{id}/status`
  - `PUT /api/tasks/{id}`

- Eureka Mock API
  - `POST /_api_/items/0/start`
  - `GET /_api_/items/0/list?sites=&detail=true`
  - `POST /_api_/items/{itemId}/complete`
  - `POST /_api_/stages/{stageId}/status`
  - `PUT /_api_/items/{itemId}`
  - `GET /_api_/items/{itemId}/status`

- WebSocket
  - `ws://localhost:8000/ws/{user_id}`
  - 마감 임계치 도달 시 `proactive_alert` 전송

- Debug API
  - 원하는 업무에 대해 즉시 alert 강제 발생
  - Mock 데이터 초기화

---

## 1. 실행

```bash
python -m venv .venv