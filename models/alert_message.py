from datetime import datetime
from bson import ObjectId


class AlertMessage:
    """Mensaje WhatsApp asociado a una alerta (auditoría + resumen para managers)"""

    DIRECTION_IN = "in"   # usuario -> sistema
    DIRECTION_OUT = "out"  # sistema -> usuario

    def __init__(self, alert_id=None, phone=None, direction=None, type=None,
                 body=None, payload=None, user_id=None, user_name=None,
                 user_role=None, is_template=False, is_navigation=False,
                 fecha=None, media_url=None, mime_type=None,
                 wa_message_id=None, wa_recipients=None, reply_to=None, reactions=None,
                 media_pending=False, _id=None):
        self._id = _id or ObjectId()
        self.alert_id = alert_id
        self.phone = phone
        self.direction = direction
        self.type = type or "text"
        self.body = body or ""
        self.payload = payload or {}
        self.user_id = user_id
        self.user_name = user_name
        self.user_role = user_role or ""
        self.is_template = bool(is_template)
        self.is_navigation = bool(is_navigation)
        self.fecha = fecha or datetime.utcnow()
        # Media descargada de WhatsApp y servida por RescueBack (imagen/audio/video/sticker).
        self.media_url = media_url
        self.mime_type = mime_type
        # True mientras la media se descarga en segundo plano (el panel muestra "cargando").
        self.media_pending = bool(media_pending)
        # Threading: id de mensaje de WhatsApp (wamid) y cita del mensaje respondido.
        # Entrante: `wa_message_id` (uno). Saliente al grupo: `wa_recipients` con un
        # {phone, wa_message_id} por contacto (WhatsApp es 1:1, cada uno recibe su wamid),
        # necesario para citar al responder y para resolver quién respondió a qué.
        self.wa_message_id = wa_message_id
        self.wa_recipients = wa_recipients or []
        self.reply_to = reply_to
        # Reacciones: {actor_key: {emoji, name}}. actor_key = digits(phone) o "empresa".
        self.reactions = reactions or {}

    def to_dict(self):
        return {
            '_id': self._id,
            'alert_id': self.alert_id,
            'phone': self.phone,
            'direction': self.direction,
            'type': self.type,
            'body': self.body,
            'payload': self.payload,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_role': self.user_role,
            'is_template': self.is_template,
            'is_navigation': self.is_navigation,
            'fecha': self.fecha,
            'media_url': self.media_url,
            'mime_type': self.mime_type,
            'media_pending': self.media_pending,
            'wa_message_id': self.wa_message_id,
            'wa_recipients': self.wa_recipients,
            'reply_to': self.reply_to,
            'reactions': self.reactions
        }

    def to_json(self):
        return {
            '_id': str(self._id),
            'alert_id': str(self.alert_id) if self.alert_id else None,
            'phone': self.phone,
            'direction': self.direction,
            'type': self.type,
            'body': self.body,
            'payload': self.payload,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_role': self.user_role,
            'is_template': self.is_template,
            'is_navigation': self.is_navigation,
            'fecha': self.fecha.isoformat() if isinstance(self.fecha, datetime) else self.fecha,
            'media_url': self.media_url,
            'mime_type': self.mime_type,
            'media_pending': self.media_pending,
            'wa_message_id': self.wa_message_id,
            'wa_recipients': self.wa_recipients,
            'reply_to': self.reply_to,
            'reactions': self.reactions
        }

    @classmethod
    def from_dict(cls, data):
        if not data:
            return None
        return cls(
            _id=data.get('_id'),
            alert_id=data.get('alert_id'),
            phone=data.get('phone'),
            direction=data.get('direction'),
            type=data.get('type', 'text'),
            body=data.get('body', ''),
            payload=data.get('payload', {}),
            user_id=data.get('user_id'),
            user_name=data.get('user_name'),
            user_role=data.get('user_role', ''),
            is_template=bool(data.get('is_template', False)),
            is_navigation=bool(data.get('is_navigation', False)),
            fecha=data.get('fecha'),
            media_url=data.get('media_url'),
            mime_type=data.get('mime_type'),
            media_pending=data.get('media_pending', False),
            wa_message_id=data.get('wa_message_id'),
            wa_recipients=data.get('wa_recipients'),
            reply_to=data.get('reply_to'),
            reactions=data.get('reactions')
        )
