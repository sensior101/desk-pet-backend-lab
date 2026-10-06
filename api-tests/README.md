# Eureka Process API Tests

Desk Pet 백엔드 연동을 위해 Eureka Process API를 실제 운영 환경에서 검증한 PoC 기록입니다.

---

## 1. Eureka Process PoC

### 1-1. 테스트 목적

Eureka Process API를 실제 운영 환경에서 호출하여 다음 항목을 확인하였다.

- API Key 기반 인증 정상 여부
- Process 및 업무 데이터 조회 가능 여부
- 업무 등록·조회·수정·완료·삭제 기능 동작 여부
- API 응답 속도
- Desk Pet 백엔드 연동 시 고려해야 할 제약사항

### 1-2. 테스트 환경

| 항목 | 내용 |
| --- | --- |
| 테스트 환경 | Windows PC |
| 개발 언어 | Python |
| HTTP Client | `requests` |
| 환경변수 처리 | `python-dotenv` |
| Eureka 환경 | 운영 환경 |
| Base URL | `https://api.eureka.codes/flw-v1` |
| Process ID | `general-work-v1@10204` |

### 1-3. 테스트 절차

PoC는 다음 순서로 진행하였다.

`API Key 확인` → `Process 확인` → `업무 등록` → `업무 목록 조회` → `업무 완료` → `상태 확인` → `마감 연기` → `업무 삭제`

### 1-4. 테스트 결과

| 테스트 종류 | 소요 시간 | 성공 여부 |
| --- | --- | --- |
| Session (API Key 인증 확인) | 0.191 / 0.468 sec | 성공 |
| Process 목록 조회 | 0.301 ~ 1.135 sec | 성공 |
| 업무 등록 | 0.672 sec | 성공 |
| 업무 조회 | 0.279 sec | 성공 |
| 업무 완료 | 0.230 sec | 성공 |
| 상태 조회 | 0.183 sec | 성공 |
| 마감 연기 | 0.126 sec | 성공 |
| 업무 삭제 | 0.404 sec | 성공 |

전체 테스트에서 API 호출은 정상적으로 동작하였다.

대부분의 요청은 약 **0.1~0.7초 내외**로 응답하였으며, Process 목록 조회에서 최대 약 **1.1초**의 응답 시간이 확인되었다.

---

## 2. PoC 과정에서 확인한 Eureka Process 제약사항

### 2-1. 마감 기한 범위 검색 미지원

Eureka API에서는 다음과 같은 조건으로 업무를 직접 조회하는 기능이 제공되지 않는다.

- 1시간 이내 마감 업무
- 오늘 마감 업무
- 특정 시간 범위 내 마감 업무

따라서 백엔드에서 업무 목록을 조회한 후 각 업무의 `dueAt` 값을 기준으로 직접 필터링해야 한다.

### 2-2. Push/Webhook 미지원

Eureka Process에서는 업무 상태 변경이나 마감 시점 도달 시 백엔드로 자동 이벤트를 전달하는 Push 또는 Webhook 기능을 제공하지 않는다.

따라서 Desk Pet 백엔드가 일정 주기로 Eureka API를 호출하는 **Polling 방식**이 필요하다.

### 2-3. 업무 상태 관리 방식

업무 완료 여부는 Item 자체의 단순 상태값보다 **하위 Stage 상태를 기반으로 관리되는 구조**를 가진다.

개별 업무의 정확한 상태는 다음 API를 통해 확인할 수 있다.

`GET /_api_/items/{itemId}/status`

다만 Polling 과정에서 여러 업무의 상태를 반복적으로 확인할 경우 각 업무마다 상태 조회 API를 호출하면 요청 횟수가 크게 증가할 수 있다.

따라서 대량 조회 상황에서는 업무 목록 데이터에 포함된 `stage$$` 값을 이용하여 상태를 우선 판단하고, 필요한 경우에만 개별 상태 조회 API를 호출하는 방식이 적합하다.

### 2-4. 오류 응답 처리

입력 데이터 검증 오류가 항상 `400 Bad Request`로 반환되지는 않았다.

일부 잘못된 요청의 경우 서버에서 `500` 응답이 반환될 수 있다.

따라서 백엔드에서는 HTTP Status Code만으로 요청 성공 여부를 판단하지 않고 다음 정보를 함께 확인해야 한다.

- HTTP Status Code
- Response Body
- Eureka에서 반환한 오류 메시지

즉, 오류 처리는 다음 기준으로 수행해야 한다.

`Status Code 확인 + Response Body 검증`

---

## 3. 테스트 코드

| 파일 | 역할 |
| --- | --- |
| `eureka_session.py` | API Key 인증 및 Session 확인 |
| `eureka_process_list.py` | Process 목록 조회 |
| `eureka_task_create.py` | 업무 등록 |
| `eureka_task_list.py` | 업무 목록 조회 |
| `eureka_task_status.py` | 업무 상태 조회 |
| `eureka_task_complete.py` | 업무 완료 처리 |
| `eureka_task_update.py` | 업무 수정 및 마감 연기 |
| `eureka_task_delete.py` | 업무 삭제 |

---

## 4. 백엔드 설계 반영사항

PoC 결과를 바탕으로 Desk Pet 백엔드는 다음 방식으로 Eureka Process와 연동한다.

- Eureka Process를 업무 데이터의 원본 시스템(Source of Truth)으로 사용한다.
- 애플리케이션 로직은 `TaskPort`를 통해 업무 시스템에 접근한다.
- 실제 Eureka HTTP 통신 및 요청/응답 변환은 `EurekaTaskAdapter`에서 처리한다.
- 마감 임박 업무 탐지는 Push/Webhook이 아닌 Polling 방식으로 구현한다.
- Polling 시 업무 목록의 `dueAt` 값을 기준으로 마감 임박 업무를 필터링한다.
- 업무 완료 여부는 목록 데이터의 `stage$$` 값을 우선 활용한다.
- 보다 정확한 상태 확인이 필요한 경우에만 개별 상태 조회 API를 호출한다.
- API 오류는 HTTP Status Code뿐 아니라 Response Body와 Eureka 오류 메시지를 함께 검증한다.

---

## 5. 환경변수

API Key는 코드에 직접 작성하지 않고 `.env` 파일을 통해 관리한다.

```env
EUREKA_API_KEY=YOUR_API_KEY