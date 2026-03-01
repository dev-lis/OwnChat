# Документация: OwnChat

## 1. Цели и принципы

- Архитектура: микросервисная.
- API Gateway: `FastAPI`.
- Хранение данных: `PostgreSQL` (по сервисам, схема `database-per-service`).
- Клиенты (web/mobile): максимально тонкие, без бизнес-логики.
- Протоколы: `REST API` + `WebSocket`.
- Версионирование API: через префикс пути `/api/v1/...`.
- Кэширование сообщений и файлов: `Redis` (оперативный кэш) + Object Storage для файлов (S3-совместимое).

## 2. Высокоуровневая архитектура

### 2.1 Сервисы

1. **API Gateway (FastAPI)**
- Единая точка входа: auth, rate limits, трассировка, роутинг.
- Агрегация ответов, если нужно.
- Проксирование REST и инициализация WebSocket-сессий.

2. **Auth Service**
- Регистрация и авторизация по номеру телефона.
- 2FA (OTP по SMS/Push/TOTP).
- Выдача JWT: `access` + `refresh`.
- Управление сессиями и устройствами.

3. **User Service**
- Профиль пользователя (минимум: id, phone, display_name, avatar_url, created_at).

4. **Chat Service**
- Создание диалогов/чатов.
- Список чатов пользователя (курсорная пагинация).
- Счетчики непрочитанных сообщений.

5. **Message Service**
- Отправка/получение сообщений.
- История сообщений с курсорной пагинацией в обе стороны.
- Статусы: `sent`, `delivered`, `read`.
- События в брокер для realtime.

6. **Media Service**
- Загрузка изображений, валидация типа/размера.
- Выдача pre-signed URL.
- Метаданные файлов.

7. **Realtime Gateway (WebSocket Service)**
- WebSocket-подключения клиентов.
- Доставка событий: новое сообщение, typing, read receipts.
- Присутствие и fan-out по участникам чата.

### 2.2 Инфраструктурные компоненты

- **PostgreSQL**: отдельная БД на сервис (или отдельные схемы при старте).
- **Redis**:
  - кэш горячих данных (последние сообщения, метаданные файлов, сессии);
  - Pub/Sub (или Streams) для realtime-событий.
- **Message Broker** (рекомендуется: NATS/Kafka/RabbitMQ): асинхронные события между сервисами.
- **Object Storage** (S3): хранение изображений/файлов.
- **Observability**: Prometheus + Grafana + OpenTelemetry + централизованные логи.

## 3. Доменная модель

### 3.1 Основные сущности

- `User`
- `Chat`
- `ChatParticipant`
- `Message`
- `MessageStatus` (по пользователю-получателю)
- `Attachment` (изображения)
- `UserChatState` (last_read_message_id, unread_count)

### 3.2 Модель сообщения

Обязательные поля сообщения:

- `id`
- `chat_id`
- `author_id`
- `type` (`text` | `image`)
- `content` (для `text`) / `attachment_id` (для `image`)
- `created_at`
- `status` (`sent` | `delivered` | `read`) — в API клиенту показывается агрегированный статус

Примечание: для групповой и точной семантики статусов хранится таблица `message_statuses` на каждого получателя.

## 4. Версионирование API

- Базовый префикс: `/api/v1`.
- Breaking changes: новый префикс `/api/v2`.
- Non-breaking changes: только добавление полей/эндпоинтов.
- WebSocket-версия: `/ws/v1`.

## 5. Аутентификация и безопасность

### 5.1 Регистрация/логин по телефону + 2FA

Поток:

1. `POST /api/v1/auth/request-otp` — отправка OTP на телефон.
2. `POST /api/v1/auth/verify-otp` — проверка OTP.
3. `POST /api/v1/auth/register` — завершение регистрации (если новый пользователь).
4. `POST /api/v1/auth/login` — выдача токенов после успешной 2FA.
5. `POST /api/v1/auth/refresh` — обновление access токена.

### 5.2 Безопасность

- JWT access token (короткоживущий, например 15 минут).
- Refresh token с ротацией и отзывом.
- TLS везде.
- Rate limit на auth/OTP/WS-handshake.
- Идемпотентность отправки сообщений через `Idempotency-Key`.

## 6. REST API (MVP-контракты)

## 6.1 Получение списка диалогов

`GET /api/v1/chats?limit=20&cursor=<token>`

Ответ:

```json
{
  "items": [
    {
      "chat_id": "uuid",
      "title": "string",
      "last_message": {
        "id": "uuid",
        "type": "text",
        "content_preview": "Привет",
        "created_at": "2026-02-28T10:00:00Z"
      },
      "unread_count": 3,
      "updated_at": "2026-02-28T10:00:00Z"
    }
  ],
  "next_cursor": "opaque_token_or_null"
}
```

## 6.2 Создание нового чата

`POST /api/v1/chats`

Тело:

```json
{
  "participant_ids": ["user-uuid-1", "user-uuid-2"],
  "title": "optional"
}
```

Ответ: `201 Created`

```json
{
  "chat_id": "uuid",
  "created_at": "2026-02-28T10:00:00Z"
}
```

## 6.3 Получение истории сообщений (двунаправленная cursor pagination)

`GET /api/v1/chats/{chat_id}/messages?limit=30&cursor=<token>&direction=older|newer`

Ответ:

```json
{
  "items": [
    {
      "id": "uuid",
      "chat_id": "uuid",
      "author_id": "uuid",
      "type": "text",
      "content": "Привет",
      "created_at": "2026-02-28T09:59:00Z",
      "status": "read"
    }
  ],
  "next_cursor": "opaque_token_or_null",
  "prev_cursor": "opaque_token_or_null"
}
```

## 6.4 Отправка сообщения

`POST /api/v1/chats/{chat_id}/messages`

Тело (`text`):

```json
{
  "type": "text",
  "content": "Привет!",
  "client_message_id": "uuid"
}
```

Тело (`image`):

```json
{
  "type": "image",
  "attachment_id": "uuid",
  "client_message_id": "uuid"
}
```

Ответ: `202 Accepted`

```json
{
  "message_id": "uuid",
  "status": "sent",
  "created_at": "2026-02-28T10:01:00Z"
}
```

## 7. WebSocket API

Endpoint: `GET /ws/v1/connect?token=<JWT>`

Формат события:

```json
{
  "event": "event_name",
  "payload": {}
}
```

### 7.1 Новое сообщение

Сервер -> клиент:

```json
{
  "event": "message.new",
  "payload": {
    "chat_id": "uuid",
    "message": {
      "id": "uuid",
      "author_id": "uuid",
      "type": "text",
      "content": "Привет",
      "created_at": "2026-02-28T10:01:00Z",
      "status": "sent"
    }
  }
}
```

### 7.2 Набор текста (typing)

Клиент -> сервер:

```json
{
  "event": "typing.start",
  "payload": {
    "chat_id": "uuid"
  }
}
```

```json
{
  "event": "typing.stop",
  "payload": {
    "chat_id": "uuid"
  }
}
```

Сервер -> клиент:

```json
{
  "event": "typing.update",
  "payload": {
    "chat_id": "uuid",
    "user_id": "uuid",
    "is_typing": true,
    "ts": "2026-02-28T10:01:05Z"
  }
}
```

### 7.3 Прочтение сообщения (read receipts)

Клиент -> сервер:

```json
{
  "event": "message.read",
  "payload": {
    "chat_id": "uuid",
    "message_id": "uuid",
    "read_at": "2026-02-28T10:02:00Z"
  }
}
```

Сервер -> клиент:

```json
{
  "event": "message.read.updated",
  "payload": {
    "chat_id": "uuid",
    "message_id": "uuid",
    "user_id": "uuid",
    "read_at": "2026-02-28T10:02:00Z"
  }
}
```

## 8. Курсорная пагинация

- Курсор непрозрачный (`opaque token`), подписанный сервером.
- Содержит `sort_key` (например `created_at`, `id`) и направление.
- Для истории сообщений поддерживаются:
  - `direction=older` (вниз по истории);
  - `direction=newer` (к более новым).

Рекомендуемая сортировка: `(created_at DESC, id DESC)` для стабильной выдачи.

## 9. Кэширование сообщений и файлов

### 9.1 Что кэшируем в Redis

- Последние N сообщений чата (`chat:{id}:recent_messages`).
- Метаданные вложений (`attachment:{id}:meta`).
- Списки диалогов пользователя (`user:{id}:chat_list:cursor:*`).
- WebSocket presence/typing (`chat:{id}:typing_users`).

### 9.2 Инвалидация

- При новом сообщении: инвалидация chat list у участников и обновление recent cache.
- При read receipt: пересчет `unread_count` и инвалидация списка чатов.
- TTL для кэша: 30-300 секунд в зависимости от типа данных.

### 9.3 Файлы

- Изображения храним в S3-совместимом хранилище.
- В Redis кэшируем только метаданные и pre-signed URL (короткий TTL).

## 10. Минимальная схема БД (пример)

```sql
CREATE TABLE chats (
  id UUID PRIMARY KEY,
  title TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chat_participants (
  chat_id UUID NOT NULL,
  user_id UUID NOT NULL,
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (chat_id, user_id)
);

CREATE TABLE messages (
  id UUID PRIMARY KEY,
  chat_id UUID NOT NULL,
  author_id UUID NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('text', 'image')),
  content TEXT,
  attachment_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE message_statuses (
  message_id UUID NOT NULL,
  user_id UUID NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('sent', 'delivered', 'read')),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (message_id, user_id)
);

CREATE TABLE user_chat_state (
  chat_id UUID NOT NULL,
  user_id UUID NOT NULL,
  last_read_message_id UUID,
  unread_count INT NOT NULL DEFAULT 0,
  PRIMARY KEY (chat_id, user_id)
);
```

## 11. Нефункциональные требования

- SLA на REST: p95 < 200 мс для read-эндпоинтов (при warm cache).
- Гарантия порядка сообщений внутри чата (по `created_at`, `id`).
- Идемпотентность отправки сообщения.
- Горизонтальное масштабирование Realtime сервиса.
- Трассировка запроса end-to-end через `trace_id`.

## 12. План реализации (этапы)

1. Базовый `API Gateway` на FastAPI + JWT middleware + versioned routing.
2. Auth Service (phone + OTP + 2FA), User Service.
3. Chat Service + Message Service + PostgreSQL схемы.
4. WebSocket Realtime Gateway + Redis Pub/Sub.
5. Media Service + Object Storage.
6. Набор контрактных тестов API и нагрузочные тесты realtime.

## 13. Открытые решения (предлагается зафиксировать)

- Провайдер 2FA (SMS): Twilio/MessageBird/локальный.
- Брокер событий: NATS vs Kafka.
- Стратегия дедупликации сообщений по `client_message_id`.
- Политика хранения медиа (retention, лимиты размеров, antivirus scanning).

## 14. Артефакты спецификации

- OpenAPI v1: `docs/openapi.yaml`
- Схемы взаимодействия сервисов: `docs/service-architecture.md`
