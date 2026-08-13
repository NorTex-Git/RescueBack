from bson import ObjectId
from core.database import Database
from models.alert_message import AlertMessage


class AlertMessageRepository:
    """Repositorio para mensajes WhatsApp asociados a alertas"""

    def __init__(self):
        self.db = Database().get_database()
        self.collection = self.db.alert_messages
        try:
            self.collection.create_index([('alert_id', 1), ('fecha', -1)])
            self.collection.create_index([('phone', 1), ('fecha', -1)])
        except Exception:
            pass

    def _coerce_alert_id(self, alert_id):
        if isinstance(alert_id, ObjectId):
            return alert_id
        if isinstance(alert_id, str):
            try:
                return ObjectId(alert_id)
            except Exception:
                return alert_id
        return alert_id

    def create(self, message: AlertMessage) -> AlertMessage:
        message.alert_id = self._coerce_alert_id(message.alert_id)
        self.collection.insert_one(message.to_dict())
        return message

    def find_by_id(self, message_id):
        """Devuelve un mensaje por su _id interno, o None."""
        try:
            doc = self.collection.find_one({'_id': ObjectId(message_id)})
        except Exception:
            doc = self.collection.find_one({'_id': message_id})
        return AlertMessage.from_dict(doc) if doc else None

    def find_by_wa_id(self, alert_id, wa_message_id):
        """Busca un mensaje por su wamid dentro de una alerta.

        Matchea tanto el wamid único (entrante) como la lista de wamids por contacto
        (mensaje saliente al grupo), para resolver la cita responda quien responda.
        """
        if not wa_message_id:
            return None
        doc = self.collection.find_one({
            'alert_id': self._coerce_alert_id(alert_id),
            '$or': [
                {'wa_message_id': wa_message_id},
                {'wa_recipients.wa_message_id': wa_message_id},
            ],
        })
        return AlertMessage.from_dict(doc) if doc else None

    def find_by_alert(self, alert_id, direction=None, limit=15, include_templates=False, include_navigation=False):
        """Devuelve los últimos `limit` mensajes ordenados por fecha asc para mostrar al usuario."""
        query = {'alert_id': self._coerce_alert_id(alert_id)}
        if direction in (AlertMessage.DIRECTION_IN, AlertMessage.DIRECTION_OUT):
            query['direction'] = direction
        if not include_templates:
            query['is_template'] = {'$ne': True}
        if not include_navigation:
            query['is_navigation'] = {'$ne': True}
        cursor = self.collection.find(query).sort('fecha', -1).limit(limit)
        docs = list(cursor)
        docs.reverse()  # cronologico ascendente para mostrar
        return [AlertMessage.from_dict(d) for d in docs]
