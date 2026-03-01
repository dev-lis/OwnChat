# Документация: OwnChat (текущее состояние backend)

## 1. Архитектурный статус

Система реализована как **modular monolith**:
- единый процесс FastAPI (API Gateway + доменные модули);
- логические границы сервисов выделены в отдельных пакетах;
- внешний API уже версионирован (`/api/v1`, `/ws/v1`);
- хранилище MVP: in-memory (`app/state/store.py`).

Это переходный этап перед физическим разделением на отдельные микросервисы.

## 2. Сервисные модули в коде

- `system`:
  - `GET /health`.
- `auth`:
  - OTP flow: `request-otp`, `verify-otp`, `register`, `login`, `refresh`.
  - temp flow: `temp-register` (login/password).
  - dependency `require_user_id`.
- `chats`:
  - список чатов, создание чатов.
- `messages`:
  - история сообщений, отправка, read receipt (REST fallback).
- `media`:
  - создание upload target.
- `realtime`:
  - WebSocket `GET /ws/v1/connect`.

## 3. Техническая композиция

- Entrypoint: `app/main.py`.
- Composition root: `app/app_factory.py`.
- OpenAPI config: `app/core/openapi.py`.
- Shared helpers: `app/core/time.py`.
- In-memory state: `app/state/store.py`.

## 4. Текущий runtime flow

### 4.1 REST flow
1. Клиент вызывает endpoint `/api/v1/...`.
2. Router соответствующего модуля обрабатывает запрос.
3. Для защищенных endpoint выполняется `require_user_id`.
4. Бизнес-логика читает/пишет in-memory store.
5. Возвращается JSON-ответ по контракту OpenAPI.

### 4.2 Realtime flow
1. Клиент открывает `ws://.../ws/v1/connect` с токеном.
2. Сервер валидирует token через `ACCESS_TOKENS`.
3. Сервер отправляет `system.connected`.
4. Для `typing.start|typing.stop` отправляется `typing.update`.
5. Для `message.read` отправляется `message.read.updated`.

## 5. Ограничения текущего этапа

- Нет персистентности (данные теряются при рестарте).
- Нет межпроцессного fan-out событий.
- Нет внешних интеграций OTP/SMS.
- Нет rate limiting, revoke-сессий и production-grade security hardening.

## 6. Целевой путь к микросервисам

### 6.1 Что уже готово
- Границы ответственности уже разнесены по модулям.
- Контракты API централизованы в `docs/openapi.yaml`.

### 6.2 Следующий шаг
- Выделить каждый модуль в отдельный deployable сервис:
  - `auth-service`, `chat-service`, `message-service`, `media-service`, `realtime-service`.
- Перевести state на PostgreSQL/Redis/Object Storage.
- Оставить FastAPI gateway как edge-контур (routing/authz/rate-limit/tracing).
