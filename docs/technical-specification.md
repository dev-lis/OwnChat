# Техническое задание (реализация проекта с нуля по текущему состоянию кода)

## 1. Общая информация

### 1.1 Наименование
`OwnChat API` (MVP backend для чата).

### 1.2 Основание для разработки
Текущее состояние зафиксировано в:
- `/Users/aleksandr/Desktop/projects/OwnChat/app/main.py`
- `/Users/aleksandr/Desktop/projects/OwnChat/app/app_factory.py`
- `/Users/aleksandr/Desktop/projects/OwnChat/app/auth/router.py`
- `/Users/aleksandr/Desktop/projects/OwnChat/app/chats/router.py`
- `/Users/aleksandr/Desktop/projects/OwnChat/app/messages/router.py`
- `/Users/aleksandr/Desktop/projects/OwnChat/app/media/router.py`
- `/Users/aleksandr/Desktop/projects/OwnChat/app/realtime/router.py`
- `/Users/aleksandr/Desktop/projects/OwnChat/docs/openapi.yaml`

### 1.3 Цель
Реализовать backend API чата с:
- аутентификацией (OTP и временный flow login/password);
- чатами и сообщениями;
- медиа upload target;
- realtime событиями по WebSocket.

### 1.4 Границы MVP
- Backend без UI.
- Версия API: `v1`.
- Реализация как modular monolith на FastAPI.
- Хранение данных на этапе MVP: in-memory.

## 2. Архитектурные требования

### 2.1 Стиль архитектуры
Обязательная реализация: **service-oriented modular monolith**.

### 2.2 Модульная декомпозиция
- `system` — health endpoint.
- `auth` — auth flows и dependency авторизации.
- `chats` — список/создание чатов.
- `messages` — история/отправка/read.
- `media` — создание upload target.
- `realtime` — WebSocket endpoint и события.
- `state` — единое in-memory состояние.
- `core` — общие инфраструктурные функции.

### 2.3 Точка сборки приложения
- `app/main.py` создает app через `app/app_factory.py`.
- Все роутеры подключаются централизованно в `create_app()`.

## 3. Функциональные требования

## 3.1 System

### FR-SYS-001 Healthcheck
- Метод: `GET /health`.
- Ответ: `200` + `{"status":"ok"}`.

## 3.2 Auth

### FR-AUTH-001 Request OTP
- `POST /api/v1/auth/request-otp`
- Вход: `phone`.
- Выход: `otp_session_id`, `expires_in`.
- В MVP OTP-код фиксированный: `123456`.

### FR-AUTH-002 Verify OTP
- `POST /api/v1/auth/verify-otp`
- Вход: `otp_session_id`, `code`.
- Ошибка: `401` при неверном коде/сессии.
- Успех: `verified`, `verification_token`.

### FR-AUTH-003 Register
- `POST /api/v1/auth/register`
- Вход: `verification_token`, `display_name`, `avatar_url?`.
- Ошибки:
- `401` при невалидном verification_token.
- `409` если пользователь уже существует.
- Успех: `201` + `user_id`, `created_at`.

### FR-AUTH-004 Login
- `POST /api/v1/auth/login`
- Вход: `verification_token`, `device_id?`.
- Ошибка: `401` если пользователь не зарегистрирован.
- Успех: `access_token`, `refresh_token`, `token_type`, `expires_in`.

### FR-AUTH-005 Refresh
- `POST /api/v1/auth/refresh`
- Вход: `refresh_token`.
- Ошибка: `401` при невалидном токене.
- Успех: новая пара токенов.

### FR-AUTH-006 Temp Register (login/password)
- `POST /api/v1/auth/temp-register`
- Вход: `login`, `password`.
- Правила login:
- минимум 3 символа;
- только латинские буквы и цифры.
- Поведение:
- если login не существует, создать пользователя и вернуть токены;
- если login существует, вернуть `409`.
- Ошибка валидации login: `400`.

## 3.3 Chats

### FR-CHAT-001 List Chats
- `GET /api/v1/chats`
- Требует Bearer токен.
- Параметры: `limit`, `cursor`.
- Ответ: `items`, `next_cursor`.

### FR-CHAT-002 Create Chat
- `POST /api/v1/chats`
- Требует Bearer токен.
- Вход: `participant_ids`, `title?`.
- Создатель всегда добавляется в участники.
- Успех: `201` + `chat_id`, `created_at`.

## 3.4 Messages

### FR-MSG-001 Message History
- `GET /api/v1/chats/{chat_id}/messages`
- Требует Bearer токен.
- Параметры: `limit`, `cursor`, `direction`.
- Ошибка: `404` при недоступном чате.
- Ответ: `items`, `next_cursor`, `prev_cursor`.

### FR-MSG-002 Send Message
- `POST /api/v1/chats/{chat_id}/messages`
- Требует Bearer токен.
- Поддержка payload:
- `text` (`content`, `client_message_id`)
- `image` (`attachment_id`, `client_message_id`)
- Успех: `202` + `message_id`, `status`, `created_at`.

### FR-MSG-003 Mark As Read
- `POST /api/v1/chats/{chat_id}/messages/read`
- Требует Bearer токен.
- Вход: `message_id`, `read_at`.
- Ошибки: `404` (чат/сообщение не найден).
- Успех: `chat_id`, `message_id`, `user_id`, `status=read`, `read_at`.

## 3.5 Media

### FR-MEDIA-001 Create Upload Target
- `POST /api/v1/media/uploads`
- Требует Bearer токен.
- Вход: `content_type`, `file_name`, `size_bytes`.
- Успех: `201` + `attachment_id`, `upload_url`, `expires_in`.

## 3.6 Realtime

### FR-WS-001 Connect
- Endpoint: `GET /ws/v1/connect`.
- Авторизация через `token` query или Bearer header.
- Невалидный токен: закрытие с кодом `1008`.
- При подключении отправляется `system.connected`.

### FR-WS-002 Typing events
- Клиент: `typing.start`, `typing.stop`.
- Сервер: `typing.update`.

### FR-WS-003 Read events
- Клиент: `message.read`.
- Сервер: `message.read.updated`.

## 4. Нефункциональные требования

## 4.1 Стек
- Python `3.10+`.
- FastAPI, Uvicorn, Pydantic, PyYAML.

## 4.2 Форматы
- JSON для REST.
- ISO 8601 UTC (`...Z`) для timestamp.

## 4.3 OpenAPI
- Обязательные endpoints документации:
- `/openapi.json`
- `/docs`
- `/redoc`
- Приоритет источника: `docs/openapi.yaml`.
- Fallback: auto-generated schema.

## 4.4 Ошибки
- Базовый формат ошибок:
- `{"code":"...","message":"..."}`.

## 5. Ограничения текущего этапа

- In-memory state без персистентности.
- Нет production-level безопасности и rate limits.
- Нет межсервисной event-шины и fan-out между процессами.

## 6. Критерии приемки

### AC-001 Auth OTP flow
1. `request-otp` возвращает `otp_session_id`.
2. `verify-otp` c `123456` возвращает `verification_token`.
3. `register` создает пользователя.
4. `login` возвращает access/refresh токены.

### AC-002 Temp Register flow
1. `temp-register` с новым login создает пользователя.
2. Ответ содержит `user_id`, `access_token`, `refresh_token`.
3. Повтор с тем же login возвращает `409`.

### AC-003 Chat/Message flow
1. Авторизованный пользователь создает чат.
2. Отправка сообщения возвращает `202`.
3. История возвращает сообщение.
4. Read endpoint возвращает `status=read`.

### AC-004 Media flow
1. `/api/v1/media/uploads` возвращает `attachment_id` и `upload_url`.

### AC-005 Realtime flow
1. WebSocket подключается с валидным токеном.
2. `typing.start` -> `typing.update`.
3. `message.read` -> `message.read.updated`.
