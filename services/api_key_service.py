import hashlib
import hmac
import secrets
from datetime import datetime

from models.api_key import ApiKey, SCOPES_VALIDOS, KEY_PREFIX_PUBLICO
from repositories.api_key_repository import ApiKeyRepository
from repositories.empresa_repository import EmpresaRepository

# Longitud del prefijo publico (en caracteres hex) usado para localizar la llave.
LONGITUD_PREFIJO = 8


class ApiKeyService:
    """Emision y validacion de llaves de API para el modulo de integracion.

    Sobre el hashing: aqui se usa SHA-256 y no bcrypt como en las contrasenas.
    bcrypt es lento a proposito para proteger secretos de baja entropia que
    elige un humano. Una llave de API es un valor aleatorio de 256 bits
    generado por `secrets`, asi que fuerza bruta sobre el hash es inviable sin
    importar la velocidad del algoritmo. Usar bcrypt aqui solo agregaria ~100ms
    a cada peticion autenticada sin ganar seguridad.
    """

    def __init__(self):
        self.repository = ApiKeyRepository()
        self.empresa_repo = EmpresaRepository()

    def _hash_key(self, llave_completa):
        """Calcula el hash almacenable de una llave completa"""
        return hashlib.sha256(llave_completa.encode('utf-8')).hexdigest()

    def _parse_key(self, llave_completa):
        """Separa una llave en (prefijo, secreto). Devuelve (None, None) si el
        formato no corresponde."""
        if not llave_completa or not isinstance(llave_completa, str):
            return None, None

        if not llave_completa.startswith(KEY_PREFIX_PUBLICO):
            return None, None

        cuerpo = llave_completa[len(KEY_PREFIX_PUBLICO):]
        # El prefijo ocupa una posicion fija, seguido de un separador.
        # No se parte por '_' porque el secreto url-safe puede contenerlo.
        if len(cuerpo) < LONGITUD_PREFIJO + 2 or cuerpo[LONGITUD_PREFIJO] != '_':
            return None, None

        prefijo = cuerpo[:LONGITUD_PREFIJO]
        secreto = cuerpo[LONGITUD_PREFIJO + 1:]
        if not secreto:
            return None, None

        return prefijo, secreto

    def create_api_key(self, empresa_id, nombre, scopes, expira_en=None):
        """Emite una llave nueva para una empresa.

        Devuelve la llave en claro UNA SOLA VEZ. No queda almacenada en ningun
        lado: si el cliente la pierde, hay que revocar y emitir otra.
        """
        try:
            empresa = self.empresa_repo.find_by_id(empresa_id)
            if not empresa:
                return {
                    'success': False,
                    'errors': ['La empresa no existe o esta inactiva']
                }

            if not isinstance(scopes, list) or len(scopes) == 0:
                return {
                    'success': False,
                    'errors': ['Debe asignarse al menos un scope']
                }

            invalidos = [s for s in scopes if s not in SCOPES_VALIDOS]
            if invalidos:
                return {
                    'success': False,
                    'errors': [f"Scopes no validos: {', '.join(invalidos)}"]
                }

            prefijo = secrets.token_hex(LONGITUD_PREFIJO // 2)
            secreto = secrets.token_urlsafe(32)
            llave_completa = f"{KEY_PREFIX_PUBLICO}{prefijo}_{secreto}"

            api_key = ApiKey(
                empresa_id=empresa._id,
                nombre=nombre,
                key_prefix=prefijo,
                key_hash=self._hash_key(llave_completa),
                scopes=scopes,
                expira_en=expira_en,
            )

            errores = api_key.validate()
            if errores:
                return {'success': False, 'errors': errores}

            self.repository.create(api_key)

            return {
                'success': True,
                'data': api_key.to_json(),
                # Se entrega una unica vez. No vuelve a estar disponible.
                'api_key': llave_completa,
                'message': 'Guarde la llave ahora: no se podra recuperar despues'
            }
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def validate_api_key(self, llave_completa):
        """Valida una llave recibida en una peticion.

        Devuelve el objeto ApiKey si es valida y vigente, None en cualquier
        otro caso. No distingue el motivo del rechazo hacia afuera para no
        filtrar si un prefijo existe.
        """
        try:
            prefijo, _secreto = self._parse_key(llave_completa)
            if not prefijo:
                return None

            api_key = self.repository.find_by_prefix(prefijo)
            if not api_key:
                return None

            # Comparacion en tiempo constante contra ataques de temporizacion
            hash_recibido = self._hash_key(llave_completa)
            if not hmac.compare_digest(hash_recibido, api_key.key_hash or ''):
                return None

            if not api_key.esta_vigente():
                return None

            self.repository.touch_last_used(api_key._id)
            return api_key
        except Exception:
            return None

    def list_api_keys(self, empresa_id, incluir_revocadas=False):
        """Lista las llaves de una empresa sin exponer secretos"""
        try:
            llaves = self.repository.find_by_empresa(empresa_id, incluir_revocadas)
            return {
                'success': True,
                'data': [llave.to_json() for llave in llaves],
                'count': len(llaves)
            }
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def revoke_api_key(self, api_key_id, empresa_id):
        """Revoca una llave verificando que pertenezca a la empresa indicada"""
        try:
            api_key = self.repository.find_by_id(api_key_id)
            if not api_key:
                return {'success': False, 'errors': ['Llave no encontrada']}

            # El dueno de la llave es quien puede revocarla
            if str(api_key.empresa_id) != str(empresa_id):
                return {'success': False, 'errors': ['Llave no encontrada']}

            self.repository.revoke(api_key_id)
            return {'success': True, 'message': 'Llave revocada'}
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}
