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

    def set_media(self, message_id, media_url, mime_type):
        """Marca la media como resuelta (o fallida) tras la descarga en segundo plano."""
        try:
            oid = ObjectId(message_id)
        except Exception:
            oid = message_id
        self.collection.update_one(
            {'_id': oid},
            {'$set': {'media_url': media_url, 'mime_type': mime_type, 'media_pending': False}},
        )
        return self.find_by_id(oid)

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

    def add_recipients(self, alert_id, origin_wa_message_id, recipients):
        """Agrega wamids de reenvío ({phone, wa_message_id}) al mensaje de origen.

        El mensaje se localiza por su wamid de autor. Devuelve True si lo encontró y
        actualizó, False si aún no existe (para que el emisor reintente). No duplica por
        teléfono (conserva el primero registrado).
        """
        if not origin_wa_message_id or not recipients:
            return False
        query = {
            'alert_id': self._coerce_alert_id(alert_id),
            'wa_message_id': origin_wa_message_id,
        }
        doc = self.collection.find_one(query, {'wa_recipients': 1})
        if not doc:
            return False
        existing = doc.get('wa_recipients') or []
        known_phones = {self._digits(r.get('phone')) for r in existing}
        nuevos = [
            r for r in recipients
            if r.get('wa_message_id') and self._digits(r.get('phone')) not in known_phones
        ]
        if nuevos:
            self.collection.update_one(query, {'$push': {'wa_recipients': {'$each': nuevos}}})
        return True

    @staticmethod
    def _digits(value):
        return ''.join(ch for ch in str(value or '') if ch.isdigit())

    def _apply_reaction(self, query, actor_key, emoji, name):
        """Set/quita reactions[actor_key] en el doc que matchee query. Devuelve el msg o None."""
        doc = self.collection.find_one(query)
        if not doc:
            return None
        if emoji:
            self.collection.update_one(
                {'_id': doc['_id']},
                {'$set': {f'reactions.{actor_key}': {'emoji': emoji, 'name': name or ''}}},
            )
        else:
            self.collection.update_one({'_id': doc['_id']}, {'$unset': {f'reactions.{actor_key}': ''}})
        return self.find_by_id(doc['_id'])

    def set_reaction_by_wa_id(self, alert_id, wa_message_id, actor_key, emoji, name):
        """Reacción entrante: ubica el mensaje por wamid (propio o de un contacto)."""
        if not wa_message_id or not actor_key:
            return None
        query = {
            'alert_id': self._coerce_alert_id(alert_id),
            '$or': [{'wa_message_id': wa_message_id}, {'wa_recipients.wa_message_id': wa_message_id}],
        }
        return self._apply_reaction(query, actor_key, emoji, name)

    def set_reaction_by_id(self, message_id, actor_key, emoji, name):
        """Reacción saliente (empresa): ubica el mensaje por su _id interno."""
        if not actor_key:
            return None
        try:
            query = {'_id': ObjectId(message_id)}
        except Exception:
            query = {'_id': message_id}
        return self._apply_reaction(query, actor_key, emoji, name)

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
