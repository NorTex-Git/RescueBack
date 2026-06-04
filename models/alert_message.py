from datetime import datetime
from bson import ObjectId


class AlertMessage:
    """Mensaje WhatsApp asociado a una alerta (auditoría + resumen para managers)"""

    DIRECTION_IN = "in"   # usuario -> sistema
    DIRECTION_OUT = "out"  # sistema -> usuario

    def __init__(self, alert_id=None, phone=None, direction=None, type=None,
                 body=None, payload=None, user_id=None, user_name=None,
                 is_template=False, is_navigation=False, fecha=None, _id=None):
        self._id = _id or ObjectId()
        self.alert_id = alert_id
        self.phone = phone
        self.direction = direction
        self.type = type or "text"
        self.body = body or ""
        self.payload = payload or {}
        self.user_id = user_id
        self.user_name = user_name
        self.is_template = bool(is_template)
        self.is_navigation = bool(is_navigation)
        self.fecha = fecha or datetime.utcnow()

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
            'is_template': self.is_template,
            'is_navigation': self.is_navigation,
            'fecha': self.fecha
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
            'is_template': self.is_template,
            'is_navigation': self.is_navigation,
            'fecha': self.fecha.isoformat() if isinstance(self.fecha, datetime) else self.fecha
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
            is_template=bool(data.get('is_template', False)),
            is_navigation=bool(data.get('is_navigation', False)),
            fecha=data.get('fecha')
        )
