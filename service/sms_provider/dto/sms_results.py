from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime


@dataclass(frozen=True)
class RequestCodeResult:
    ok: bool
    phone: str
    cooldown_seconds_left: int = 0
    daily_limit_left: int = 0
    banned_until: Optional[datetime] = None
    provider: str = "none"
    error: Optional[str] = None
    code_id: Optional[int] = None


@dataclass(frozen=True)
class VerifyCodeResult:
    ok: bool
    phone: str
    status: str
    attempts_left: int = 0
    banned_until: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class SendSMSResult:
    ok: bool
    provider: str
    provider_message_id: Optional[str] = None
    raw: Any = None
    error: Optional[str] = None