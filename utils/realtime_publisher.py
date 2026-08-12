"""Publicador no bloqueante de eventos de dominio hacia el gateway realtime."""

import logging
import threading

import requests

from core.config import Config


def publish_realtime_event(event: dict) -> None:
    def _fire():
        try:
            requests.post(
                f"{Config.MQTT_SERVICE_URL}/internal/realtime-event",
                json=event,
                timeout=5,
            )
        except Exception as exc:
            logging.getLogger(__name__).warning("Gateway realtime no disponible: %s", exc)

    threading.Thread(target=_fire, daemon=True).start()
