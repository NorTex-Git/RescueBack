"""Tickets HMAC cortos para autenticar conexiones realtime del navegador."""

import base64
import hashlib
import hmac
import json
import secrets
import time

from core.config import Config


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def create_realtime_ticket(user_id: str, role: str) -> tuple[str, int]:
    """Crea un ticket firmado sin exponer el JWT HTTPOnly al WebSocket."""
    expires_at = int(time.time()) + Config.REALTIME_TICKET_TTL_SECONDS
    payload = {
        "sub": str(user_id),
        "role": role,
        "empresa_id": str(user_id) if role == "empresa" else "*",
        "exp": expires_at,
        "nonce": secrets.token_urlsafe(12),
    }
    encoded = _b64url(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = _b64url(
        hmac.new(
            Config.REALTIME_SECRET.encode("utf-8"),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).digest()
    )
    return f"{encoded}.{signature}", expires_at


def verify_realtime_ticket(ticket: str):
    """Verifica firma y vencimiento; el gateway consume el nonce por separado."""
    if not ticket or "." not in ticket:
        return None
    encoded, supplied = ticket.split(".", 1)
    expected = _b64url(
        hmac.new(
            Config.REALTIME_SECRET.encode("utf-8"),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).digest()
    )
    if not hmac.compare_digest(expected, supplied):
        return None
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
        if int(payload.get("exp", 0)) <= int(time.time()):
            return None
        if payload.get("role") not in ("empresa", "super_admin"):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
