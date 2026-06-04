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

    def find_by_alert(self, alert_id, direction=None, limit=15, include_templates=False):
        """Devuelve los últimos `limit` mensajes ordenados por fecha asc para mostrar al usuario."""
        query = {'alert_id': self._coerce_alert_id(alert_id)}
        if direction in (AlertMessage.DIRECTION_IN, AlertMessage.DIRECTION_OUT):
            query['direction'] = direction
        if not include_templates:
            query['is_template'] = {'$ne': True}
        cursor = self.collection.find(query).sort('fecha', -1).limit(limit)
        docs = list(cursor)
        docs.reverse()  # cronologico ascendente para mostrar
        return [AlertMessage.from_dict(d) for d in docs]
