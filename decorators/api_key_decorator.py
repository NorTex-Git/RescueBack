from functools import wraps
from flask import jsonify, g, request

# Los imports de utils.permissions y del servicio se hacen dentro de las
# funciones a proposito: core/__init__.py carga routes -> controllers ->
# utils.permissions, asi que importar permissions en tiempo de modulo genera
# un ciclo si este archivo se carga antes que core. Diferirlo tambien permite
# testear el decorator sin levantar Mongo.

# El servicio se instancia perezosamente: su repositorio abre conexion a Mongo
# al construirse y no queremos hacerlo en tiempo de import.
_api_key_service = None


def _get_service():
    global _api_key_service
    if _api_key_service is None:
        from services.api_key_service import ApiKeyService
        _api_key_service = ApiKeyService()
    return _api_key_service


def _extraer_llave():
    """Obtiene la llave del header Authorization: Bearer <llave>"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    return auth_header[len('Bearer '):].strip() or None


def _es_llave_de_api(valor):
    """Distingue una llave de integracion de un JWT de sesion"""
    from models.api_key import KEY_PREFIX_PUBLICO
    return bool(valor) and valor.startswith(KEY_PREFIX_PUBLICO)


def require_api_key(scopes=None):
    """Exige una llave de API valida con los scopes indicados.

    Deja en el contexto de la peticion:
        g.empresa_id      -> empresa dueña de la llave
        g.auth_type       -> 'api_key'
        g.api_key_id      -> id de la llave usada (para auditoria)
        g.api_key_scopes  -> scopes concedidos

    El empresa_id SIEMPRE sale de la llave. Nunca del path ni del body.
    """
    scopes_requeridos = scopes or []

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            llave = _extraer_llave()
            if not llave:
                return jsonify({
                    'success': False,
                    'errors': ['Llave de API requerida']
                }), 401

            api_key = _get_service().validate_api_key(llave)
            if not api_key:
                return jsonify({
                    'success': False,
                    'errors': ['Llave de API invalida o revocada']
                }), 401

            faltantes = [s for s in scopes_requeridos if not api_key.tiene_scope(s)]
            if faltantes:
                return jsonify({
                    'success': False,
                    'errors': [f"Scopes insuficientes. Requiere: {', '.join(faltantes)}"]
                }), 403

            g.empresa_id = str(api_key.empresa_id)
            g.auth_type = 'api_key'
            g.api_key_id = str(api_key._id)
            g.api_key_scopes = api_key.scopes
            g.role = 'empresa'

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_api_key_or_session(scopes=None):
    """Acepta llave de API (integracion externa) o cookie de sesion (panel).

    Ambos caminos terminan dejando g.empresa_id y g.role, de modo que el
    controlador que viene despues es identico en los dos casos.
    """
    scopes_requeridos = scopes or []

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            llave = _extraer_llave()

            if _es_llave_de_api(llave):
                return require_api_key(scopes_requeridos)(f)(*args, **kwargs)

            # Camino de sesion: el decorator existente ya deja g.role y,
            # para rol empresa, g.empresa_id
            from utils.permissions import require_empresa_or_admin_token

            @require_empresa_or_admin_token
            def _con_sesion(*a, **kw):
                g.auth_type = 'session'
                return f(*a, **kw)

            return _con_sesion(*args, **kwargs)

        return decorated_function

    return decorator
