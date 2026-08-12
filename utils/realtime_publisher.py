"""Publicador no bloqueante de eventos de dominio hacia el gateway realtime."""

import logging
import threading
import time
import uuid
from datetime import datetime, timezone

import requests

from core.config import Config


def publish_realtime_event(event: dict) -> None:
    """Publish a normalized, retryable realtime domain event.

    The identifier is created before the background thread starts so every retry
    represents the same logical event and clients can safely deduplicate it.
    """
    normalized = {
        **event,
        "eventId": event.get("eventId") or str(uuid.uuid4()),
        "version": event.get("version") or 1,
        "occurredAt": event.get("occurredAt") or datetime.now(timezone.utc).isoformat(),
    }

    def _fire():
        logger = logging.getLogger(__name__)
        url = f"{Config.MQTT_SERVICE_URL}/internal/realtime-event"
        for attempt in range(1, 4):
            try:
                response = requests.post(url, json=normalized, timeout=5)
                if response.status_code == 200:
                    return
                logger.warning(
                    "Evento realtime rechazado (intento %s/3): HTTP %s %s",
                    attempt,
                    response.status_code,
                    response.text[:300],
                )
            except Exception as exc:
                logger.warning(
                    "Gateway realtime no disponible (intento %s/3): %s",
                    attempt,
                    exc,
                )
            if attempt < 3:
                time.sleep(attempt)

    threading.Thread(target=_fire, daemon=True).start()
