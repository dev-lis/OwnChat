,еапк=7# Техническое задание (реализация проекта с нуля по текущему состоянию кода)

## 1. Общая информация

### 1.1 Наименование
`OwnChat API` (MVP backend для чата).

### 1.2 Основание для разработки
Текущее поведение системы зафиксировано в:
- `/Users/aleksandr/Desktop/projects/OwnChat/app/main.py`
- `/Users/aleksandr/Desktop/projects/OwnChat/docs/openapi.yaml`
- `/Users/aleksandr/Desktop/projects/OwnChat/docs/chat-backend-architecture.md`
- `/Users/aleksandr/Desktop/projects/OwnChat/docs/service-architecture.md`

### 1.3 Цель
Реализовать backend API чата с телефонной аутентификацией через OTP, операциями с чатами/сообщениями, загрузкой медиа и realtime-событиями по WebSocket.

### 1.4 Границы MVP
- Backend без UI.
- Версия API: `v1`.
- Базовый URL локальной разработки: `http://localhost:8000`.
- В рамках текущего состояния допускается in-memory хранение данных (без персистентности между перезапусками).

## 2. Термины и сущности

- `User`: пользователь системы.
- `Chat`: диалог/чат с участниками.
- `Message`: сообщение в чате (`text` или `image`).
- `Attachment`: метаданные загружаемого файла.
- `OTP Session`: временная сессия проверки кода.
- `Verification Token`: токен, подтверждающий успешную проверку OTP.
- `Access Token` / `Refresh Token`: токены авторизации.

## 3. Функциональные требования

## 3.1 Системные endpoints

### FR-SYS-001 Healthcheck
- Метод: `GET /health`
- Результат: `200` + JSON `{"status":"ok"}`.

## 3.2 Аутентификация

### FR-AUTH-001 Запрос OTP
- Метод: `POST /api/v1/auth/request-otp`
- Вход: `phone` (string).
- Выход: `otp_session_id` (string), `expires_in` (int, секунды).
- Для MVP используется фиксированный OTP-код `123456`.

### FR-AUTH-002 Верификация OTP
- Метод: `POST /api/v1/auth/verify-otp`
- Вход: `otp_session_id`, `code` (длина 4..8).
- Ошибка: `401 unauthorized` при неверном коде/сессии.
- Успех: `verified=true`, `verification_token`.

### FR-AUTH-003 Регистрация пользователя
- Метод: `POST /api/v1/auth/register`
- Вход: `verification_token`, `display_name` (1..64), `avatar_url?`.
- Ошибки:
- `401 unauthorized`, если `verification_token` невалиден.
- `409 conflict`, если пользователь уже зарегистрирован по телефону.
- Успех: `201` + `user_id`, `created_at`.

### FR-AUTH-004 Логин
- Метод: `POST /api/v1/auth/login`
- Вход: `verification_token`, `device_id?`.
- Ошибка: `401 unauthorized`, если пользователь не зарегистрирован.
- Успех: `200` + `access_token`, `refresh_token`, `token_type=Bearer`, `expires_in=900`.

### FR-AUTH-005 Обновление токена
- Метод: `POST /api/v1/auth/refresh`
- Вход: `refresh_token`.
- Ошибка: `401 unauthorized` при невалидном токене.
- Успех: новый `access_token` + `refresh_token`.

## 3.3 Чаты

### FR-CHAT-001 Получение списка чатов
- Метод: `GET /api/v1/chats`
- Авторизация: `Bearer <access_token>`.
- Query:
- `limit` (1..100, default 20)
- `cursor` (string, опционально)
- Возвращает только чаты, где текущий пользователь участник.
- Сортировка: `updated_at` по убыванию.
- Формат ответа: `items[]`, `next_cursor`.
- `unread_count` в MVP всегда `0`.

### FR-CHAT-002 Создание чата
- Метод: `POST /api/v1/chats`
- Авторизация: обязательна.
- Вход: `participant_ids[]`, `title?`.
- Система всегда добавляет автора запроса в список участников.
- Успех: `201` + `chat_id`, `created_at`.
- Если `title` не передан, использовать `"New chat"`.

## 3.4 Сообщения

### FR-MSG-001 Получение истории сообщений
- Метод: `GET /api/v1/chats/{chat_id}/messages`
- Авторизация: обязательна.
- Query:
- `limit` (1..100, default 20)
- `cursor` (string, опционально)
- `direction` (`older` | `newer`, default `older`)
- Ошибка: `404 not_found`, если чат не существует или пользователь не участник.
- Ответ: `items[]`, `next_cursor`, `prev_cursor`.

### FR-MSG-002 Отправка сообщения
- Метод: `POST /api/v1/chats/{chat_id}/messages`
- Авторизация: обязательна.
- Поддерживаемые payload:
- `text`: `type="text"`, `content`, `client_message_id`
- `image`: `type="image"`, `attachment_id`, `client_message_id`
- Ошибка: `404 not_found`, если чат недоступен.
- Успех: `202` + `message_id`, `status="sent"`, `created_at`.
- Побочный эффект: обновление `chat.updated_at`.

### FR-MSG-003 Пометка как прочитанное (REST fallback)
- Метод: `POST /api/v1/chats/{chat_id}/messages/read`
- Авторизация: обязательна.
- Вход: `message_id`, `read_at`.
- Ошибки:
- `404 not_found`, если чат недоступен.
- `404 not_found`, если сообщение не найдено.
- Успех: `chat_id`, `message_id`, `user_id`, `status="read"`, `read_at`.

## 3.5 Медиа

### FR-MEDIA-001 Создание upload target
- Метод: `POST /api/v1/media/uploads`
- Авторизация: обязательна.
- Вход: `content_type`, `file_name`, `size_bytes > 0`.
- Успех: `201` + `attachment_id`, `upload_url`, `expires_in=300`.
- В MVP `upload_url` возвращается в виде заглушки `https://s3.example.com/upload/{attachment_id}`.

## 3.6 Realtime (WebSocket)

### FR-WS-001 Подключение
- Endpoint: `GET /ws/v1/connect` (upgrade to WebSocket).
- Авторизация через `token` query param или `Authorization: Bearer ...`.
- При невалидном токене соединение закрывается кодом `1008`.
- При успешном подключении отправляется событие:
- `system.connected` с `user_id`, `ts`.

### FR-WS-002 События typing
- Клиентские входящие события: `typing.start`, `typing.stop`.
- Серверный ответ: `typing.update` с `chat_id`, `user_id`, `is_typing`, `ts`.

### FR-WS-003 События прочтения
- Клиентское событие: `message.read` (`chat_id`, `message_id`, `read_at?`).
- Серверный ответ: `message.read.updated` с `chat_id`, `message_id`, `user_id`, `read_at`.

## 4. Нефункциональные требования

## 4.1 Технологический стек
- Python 3.11+.
- FastAPI.
- Uvicorn.
- Pydantic.
- PyYAML.

## 4.2 Формат данных
- Все API ответы и запросы: `application/json`.
- Временные метки: ISO 8601 UTC (`...Z`).

## 4.3 Безопасность
- Для защищенных endpoints обязательна Bearer-аутентификация.
- Неавторизованный доступ должен возвращать `401`.
- Ошибки должны возвращаться в формате:
- `{"code":"...", "message":"..."}`

## 4.4 Производительность (MVP минимальные требования)
- Время ответа для локального окружения при in-memory работе: p95 до 150 мс при низкой нагрузке.
- Поддержка минимум 100 одновременных WebSocket-подключений в dev-среде без деградации критических функций.

## 4.5 Наблюдаемость
- Минимум структурированные логи HTTP и WebSocket-событий.
- Healthcheck endpoint обязателен.

## 5. Архитектурные требования

## 5.1 Базовый вариант (обязательный)
- Реализация как единое FastAPI-приложение (modular monolith), полностью повторяющее текущее поведение.

## 5.2 Целевой вариант (дальнейшее развитие)
- Подготовить границы модулей под выделение в сервисы: `Auth`, `User`, `Chat`, `Message`, `Media`, `Realtime`.
- Сохранить контракт API `/api/v1` и `/ws/v1`.

## 5.3 Хранение данных
- На этапе MVP допускается in-memory (как сейчас).
- Для production-этапа предусмотреть PostgreSQL + Redis + object storage, не меняя внешний API.

## 6. OpenAPI и документация

### FR-DOC-001 OpenAPI
- Приложение должно публиковать:
- `/openapi.json`
- `/docs` (Swagger UI)
- `/redoc`

### FR-DOC-002 Источник схемы
- При наличии корректного `docs/openapi.yaml` использовать его как первичный источник схемы.
- При отсутствии/ошибке YAML выполнять fallback на auto-generated OpenAPI.

## 7. Ограничения и допущения текущего состояния

- OTP фиксированный, внешней SMS-интеграции нет.
- Токены хранятся in-memory и теряются при рестарте.
- Нет реальной доставки событий другим участникам чата (WebSocket обрабатывает события в пределах текущего соединения).
- Нет постоянного хранения сообщений и файлов.
- Нет rate limiting, device/session management, revoke-токенов и полноценных delivery/read-моделей по получателям.

## 8. Критерии приемки

### AC-001 Smoke Flow Auth
1. Запрос OTP возвращает `otp_session_id`.
2. Верификация кода `123456` возвращает `verification_token`.
3. Регистрация создает пользователя.
4. Логин возвращает `access_token` и `refresh_token`.

### AC-002 Smoke Flow Chats/Messages
1. Авторизованный пользователь создает чат.
2. Отправка `text` сообщения возвращает `202` и `message_id`.
3. История сообщений возвращает отправленное сообщение.
4. Пометка сообщения как прочитанного возвращает `status=read`.

### AC-003 Smoke Flow Media
1. Авторизованный запрос на `/api/v1/media/uploads` возвращает `attachment_id` и `upload_url`.

### AC-004 Smoke Flow WebSocket
1. Подключение с валидным токеном устанавливается.
2. При `typing.start` приходит `typing.update` с `is_typing=true`.
3. При `message.read` приходит `message.read.updated`.

## 9. Состав поставки

- Исходный код backend-приложения.
- OpenAPI-спецификация.
- README с инструкцией запуска.
- Набор smoke-тестов для ключевых сценариев из раздела 8.

