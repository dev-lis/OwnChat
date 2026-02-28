# Схема архитектуры и взаимодействия сервисов

## 1. Контейнерная схема (микросервисы)

```mermaid
flowchart LR
    C1[Web Client] --> G[FastAPI API Gateway]
    C2[Mobile Client] --> G

    G --> A[Auth Service]
    G --> U[User Service]
    G --> CH[Chat Service]
    G --> M[Message Service]
    G --> MD[Media Service]
    C1 <-->|WebSocket /ws/v1| RT[Realtime Gateway]
    C2 <-->|WebSocket /ws/v1| RT

    A --> AP[(PostgreSQL Auth DB)]
    U --> UP[(PostgreSQL User DB)]
    CH --> CHP[(PostgreSQL Chat DB)]
    M --> MP[(PostgreSQL Message DB)]
    MD --> MDP[(PostgreSQL Media DB)]

    M --> B[(Message Broker)]
    RT --> B

    CH <--> R[(Redis Cache/PubSub)]
    M <--> R
    RT <--> R
    A <--> R

    MD --> S3[(S3 Object Storage)]
```

## 2. Поток отправки и доставки сообщения

```mermaid
sequenceDiagram
    autonumber
    participant Client as Client (Web/Mobile)
    participant Gateway as API Gateway (FastAPI)
    participant Msg as Message Service
    participant Chat as Chat Service
    participant DB as PostgreSQL (Message DB)
    participant Broker as Message Broker
    participant RT as Realtime Gateway
    participant Redis as Redis

    Client->>Gateway: POST /api/v1/chats/{chat_id}/messages
    Gateway->>Msg: Validate JWT + forward
    Msg->>Chat: Check membership/permissions
    Chat-->>Msg: OK
    Msg->>DB: Insert message + statuses(sent)
    Msg->>Redis: Update chat recent cache
    Msg->>Broker: Publish message.created
    Msg-->>Gateway: 202 Accepted (message_id, sent)
    Gateway-->>Client: 202 Accepted

    Broker-->>RT: message.created
    RT->>Redis: Resolve online recipients/presence
    RT-->>Client: WS event message.new
    RT->>Msg: delivered ack (optional internal API/event)
    Msg->>DB: Update statuses(delivered)
```

## 3. Поток аутентификации (phone + OTP + 2FA)

```mermaid
sequenceDiagram
    autonumber
    participant Client as Client
    participant Gateway as API Gateway (FastAPI)
    participant Auth as Auth Service
    participant Redis as Redis
    participant SMS as SMS Provider

    Client->>Gateway: POST /api/v1/auth/request-otp (phone)
    Gateway->>Auth: request_otp(phone)
    Auth->>Redis: Save otp_session + ttl
    Auth->>SMS: Send OTP code
    Auth-->>Gateway: otp_session_id, expires_in
    Gateway-->>Client: 200 OK

    Client->>Gateway: POST /api/v1/auth/verify-otp (otp_session_id, code)
    Gateway->>Auth: verify_otp(...)
    Auth->>Redis: Validate OTP and attempts
    Auth-->>Gateway: verified=true, verification_token
    Gateway-->>Client: 200 OK

    Client->>Gateway: POST /api/v1/auth/login (verification_token, device_id)
    Gateway->>Auth: login(...)
    Auth->>Redis: Save refresh session + device
    Auth-->>Gateway: access_token, refresh_token
    Gateway-->>Client: 200 OK
```

## 4. Поток read receipt

```mermaid
sequenceDiagram
    autonumber
    participant Client as Client
    participant RT as Realtime Gateway
    participant Msg as Message Service
    participant DB as PostgreSQL (Message DB)
    participant Broker as Message Broker

    Client->>RT: WS event message.read
    RT->>Msg: read receipt (chat_id, message_id, read_at)
    Msg->>DB: Update message_statuses(read)
    Msg->>Broker: Publish message.read.updated
    Broker-->>RT: message.read.updated
    RT-->>Client: WS event message.read.updated
```

## 5. Где находится бизнес-логика

- Вся бизнес-логика в backend-сервисах (`Auth`, `Chat`, `Message`, `Media`).
- Клиент только отображает состояние и отправляет команды (`REST`/`WebSocket`).
- `API Gateway` не хранит доменную логику, только входной контур (authn, routing, limits, tracing).

## 6. Границы ответственности

- `Auth Service`: OTP/2FA, токены, сессии.
- `Chat Service`: чаты, участники, unread counters.
- `Message Service`: создание сообщений, история, статусы доставки/прочтения.
- `Media Service`: загрузка и валидация изображений, metadata + presigned URL.
- `Realtime Gateway`: живые события и fan-out в подключенные клиенты.
