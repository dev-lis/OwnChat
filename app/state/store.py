from __future__ import annotations

import re
from typing import Any

OTP_SESSIONS: dict[str, dict[str, Any]] = {}
VERIFICATION_TOKENS: dict[str, str] = {}
USERS_BY_PHONE: dict[str, dict[str, Any]] = {}
USERS_BY_LOGIN: dict[str, dict[str, Any]] = {}
ACCESS_TOKENS: dict[str, str] = {}
REFRESH_TOKENS: dict[str, str] = {}
CHATS: dict[str, dict[str, Any]] = {}
MESSAGES_BY_CHAT: dict[str, list[dict[str, Any]]] = {}
ATTACHMENTS: dict[str, dict[str, Any]] = {}

LOGIN_RE = re.compile(r"^[A-Za-z0-9]{3,}$")
