# Схема архитектуры и декомпозиции сервисов

## 1. Текущая реализация (as-is)

```mermaid
flowchart LR
    C1["Web Client"] --> G["FastAPI App (Single Process)"]
    C2["Mobile Client"] --> G

    G --> SYS["system module"]
    G --> AUTH["auth module"]
    G --> CHAT["chats module"]
    G --> MSG["messages module"]
    G --> MEDIA["media module"]
    C1 <-->|"WebSocket /ws/v1"| RT["realtime module"]
    C2 <-->|"WebSocket /ws/v1"| RT

    AUTH --> MEM[("In-memory store")]
    CHAT --> MEM
    MSG --> MEM
    MEDIA --> MEM
    RT --> MEM
```

## 2. Целевая архитектура (to-be)

```mermaid
flowchart LR
    C1["Web Client"] --> GW["API Gateway"]
    C2["Mobile Client"] --> GW

    GW --> A["Auth Service"]
    GW --> CH["Chat Service"]
    GW --> M["Message Service"]
    GW --> MD["Media Service"]
    C1 <-->|"WebSocket /ws/v1"| RT["Realtime Service"]
    C2 <-->|"WebSocket /ws/v1"| RT

    A --> AP[("PostgreSQL Auth")]
    CH --> CHP[("PostgreSQL Chat")]
    M --> MP[("PostgreSQL Message")]
    MD --> S3[("S3/Object Storage")]

    M --> B[("Message Broker")]
    RT --> B
    A <--> R[("Redis")]
    CH <--> R
    M <--> R
    RT <--> R
```

## 3. Последовательность миграции

1. Стабилизировать контракты API и добавить контрактные тесты.
2. Вынести `state/store.py` в отдельный слой репозиториев.
3. Подменить in-memory репозитории на PostgreSQL/Redis-реализации.
4. Выделить `auth` как отдельный сервис и проксировать через gateway.
5. Выделить `chats` и `messages` с event-шиной для realtime.
6. Выделить `media` с object storage и presigned URL.
7. Выделить `realtime` в отдельный процесс с pub/sub.

## 4. Границы ответственности (target)

- `auth-service`: OTP/login flows, token issue/refresh, sessions.
- `chat-service`: chats, participants, unread counters.
- `message-service`: message write/read, history, statuses, events.
- `media-service`: upload orchestration, file metadata.
- `realtime-service`: WS sessions, fan-out, typing/read notifications.
- `api-gateway`: edge-auth, routing, limits, tracing, unified API surface.

## 5. Совместимость API

Во всех этапах миграции должны сохраняться:
- REST-префикс `/api/v1`;
- WebSocket endpoint `/ws/v1/connect`;
- форматы ошибок и payload из `docs/openapi.yaml`.
