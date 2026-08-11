from datetime import datetime
from bson import ObjectId

# Scopes disponibles para el modulo de integracion externa.
SCOPES_VALIDOS = [
    'alerts:read',
    'alerts:write',
    'hardware:read',
    'hardware:write',
    'webhooks:manage',
]

# Prefijo visible de toda llave emitida. Permite identificarla en logs
# y buscarla en base de datos sin conocer el secreto completo.
KEY_PREFIX_PUBLICO = 'eco_live_'


class ApiKey:
    def __init__(
        self,
        empresa_id=None,
        nombre=None,
        key_prefix=None,
        key_hash=None,
        scopes=None,
        last_used_at=None,
        expira_en=None,
        activa=True,
        _id=None,
    ):
        self._id = _id or ObjectId()
        self.empresa_id = empresa_id
        self.nombre = nombre
        self.key_prefix = key_prefix
        self.key_hash = key_hash
        self.scopes = scopes or []
        self.last_used_at = last_used_at
        self.expira_en = expira_en
        self.activa = activa
        self.fecha_creacion = datetime.utcnow()
        self.fecha_actualizacion = datetime.utcnow()

    def to_dict(self):
        """Convierte el objeto ApiKey a diccionario para MongoDB"""
        api_key_dict = {
            'empresa_id': self.empresa_id,
            'nombre': self.nombre,
            'key_prefix': self.key_prefix,
            'key_hash': self.key_hash,
            'scopes': self.scopes,
            'last_used_at': self.last_used_at,
            'expira_en': self.expira_en,
            'activa': self.activa,
            'fecha_creacion': self.fecha_creacion,
            'fecha_actualizacion': self.fecha_actualizacion,
        }
        if self._id:
            api_key_dict['_id'] = self._id
        return api_key_dict

    @classmethod
    def from_dict(cls, data):
        """Crea un objeto ApiKey desde un diccionario de MongoDB"""
        api_key = cls()
        api_key._id = data.get('_id')
        api_key.empresa_id = data.get('empresa_id')
        api_key.nombre = data.get('nombre')
        api_key.key_prefix = data.get('key_prefix')
        api_key.key_hash = data.get('key_hash')
        api_key.scopes = data.get('scopes', [])
        api_key.last_used_at = data.get('last_used_at')
        api_key.expira_en = data.get('expira_en')
        api_key.activa = data.get('activa', True)
        api_key.fecha_creacion = data.get('fecha_creacion')
        api_key.fecha_actualizacion = data.get('fecha_actualizacion')
        return api_key

    def to_json(self):
        """Convierte a JSON serializable. Nunca expone el hash de la llave."""
        return {
            '_id': str(self._id) if self._id else None,
            'empresa_id': str(self.empresa_id) if self.empresa_id else None,
            'nombre': self.nombre,
            'key_prefix': self.key_prefix,
            'scopes': self.scopes,
            'last_used_at': self.last_used_at.isoformat() if isinstance(self.last_used_at, datetime) else self.last_used_at,
            'expira_en': self.expira_en.isoformat() if isinstance(self.expira_en, datetime) else self.expira_en,
            'activa': self.activa,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
        }

    def validate(self):
        """Valida los datos de la llave de API"""
        errors = []

        if not self.empresa_id:
            errors.append("El ID de la empresa es obligatorio")

        if not self.nombre or len(str(self.nombre).strip()) == 0:
            errors.append("El nombre de la llave es obligatorio")
        elif len(str(self.nombre).strip()) > 100:
            errors.append("El nombre no puede exceder 100 caracteres")

        if not self.key_prefix:
            errors.append("El prefijo de la llave es obligatorio")

        if not self.key_hash:
            errors.append("El hash de la llave es obligatorio")

        if not isinstance(self.scopes, list) or len(self.scopes) == 0:
            errors.append("Debe asignarse al menos un scope")
        else:
            invalidos = [s for s in self.scopes if s not in SCOPES_VALIDOS]
            if invalidos:
                errors.append(f"Scopes no validos: {', '.join(invalidos)}")

        return errors

    def esta_vigente(self):
        """Indica si la llave puede usarse en este momento"""
        if not self.activa:
            return False
        if self.expira_en and datetime.utcnow() > self.expira_en:
            return False
        return True

    def tiene_scope(self, scope):
        """Verifica si la llave tiene un scope especifico"""
        return scope in (self.scopes or [])

    def update_timestamp(self):
        """Actualiza el timestamp de modificacion"""
        self.fecha_actualizacion = datetime.utcnow()

    def normalize_data(self):
        """Normaliza los datos antes de guardar"""
        if self.nombre:
            self.nombre = str(self.nombre).strip()
        if self.scopes and isinstance(self.scopes, list):
            self.scopes = sorted({str(s).strip() for s in self.scopes if str(s).strip()})
