from functools import wraps
from flask import jsonify, g, request
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt,
    get_jwt_identity,
    JWTManager,
)
from utils.auth_utils import get_auth_cookie, get_auth_header
import jwt
from core.config import Config


def _deny_cross_tenant_access(kwargs):
    """Impide que un token empresa opere sobre el id de otra empresa."""
    if getattr(g, 'role', None) != 'empresa':
        return None

    target_empresa_id = kwargs.get('empresa_id')
    if target_empresa_id is not None and str(target_empresa_id) != str(g.empresa_id):
        return jsonify({
            "success": False,
            "errors": ["No tienes permisos para acceder a otra empresa"],
        }), 403
    return None


def require_super_admin_token(f):
    """Solo permite acceso a super_admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Intentar obtener el token de las cookies primero
            auth_token = request.cookies.get('auth_token')
            # print(f"Debug: Cookie auth_token: {auth_token[:50] if auth_token else 'None'}...")
            
            if not auth_token:
                # Si no hay cookie, intentar con header Authorization
                auth_header = request.headers.get('Authorization')
                # print(f"Debug: Auth header: {auth_header}")
                if auth_header and auth_header.startswith('Bearer '):
                    auth_token = auth_header.replace('Bearer ', '')
                    # Verificar que no sea el placeholder 'cookie_auth'
                    if auth_token == 'cookie_auth':
                        auth_token = None
            
            if not auth_token:
                # print("Debug: No se encontró token válido")
                return (
                    jsonify({"success": False, "errors": ["Token de autenticación requerido"]}),
                    401,
                )
            
            # Decodificar el token manualmente
            try:
                claims = jwt.decode(
                    auth_token,
                    Config.JWT_SECRET_KEY,
                    algorithms=['HS256']
                )
                # print(f"Debug: Claims decodificados: {claims}")
            except jwt.ExpiredSignatureError:
                # print("Debug: Token expirado")
                return (
                    jsonify({"success": False, "errors": ["Token expirado"]}),
                    401,
                )
            except jwt.InvalidTokenError as e:
                # print(f"Debug: Token inválido: {e}")
                return (
                    jsonify({"success": False, "errors": ["Token inválido"]}),
                    401,
                )
            
            if claims.get("role") != "super_admin":
                # print(f"Debug: Rol incorrecto: {claims.get('role')}")
                return (
                    jsonify({"success": False, "errors": ["Permiso de super admin requerido"]}),
                    401,
                )
            
            g.user_id = claims.get('sub')
            g.role = "super_admin"
            # print(f"Debug: Autenticación exitosa para usuario {g.user_id}")
            return f(*args, **kwargs)
            
        except Exception as e:
            # print(f"Error en require_super_admin_token: {e}")
            # print(f"Cookies recibidas: {dict(request.cookies)}")
            # print(f"Headers recibidos: {dict(request.headers)}")
            return (
                jsonify({"success": False, "errors": ["Error de autenticación"]}),
                422,
            )
    return decorated_function


def require_empresa_token(f):
    """Solo permite acceso a empresa"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Intentar obtener el token de las cookies primero
            auth_token = request.cookies.get('auth_token')
            
            if not auth_token:
                # Si no hay cookie, intentar con header Authorization
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    auth_token = auth_header.replace('Bearer ', '')
                    # Verificar que no sea el placeholder 'cookie_auth'
                    if auth_token == 'cookie_auth':
                        auth_token = None
            
            if not auth_token:
                return (
                    jsonify({"success": False, "errors": ["Token de autenticación requerido"]}),
                    401,
                )
            
            # Decodificar el token manualmente
            try:
                claims = jwt.decode(
                    auth_token,
                    Config.JWT_SECRET_KEY,
                    algorithms=['HS256']
                )
            except jwt.ExpiredSignatureError:
                return (
                    jsonify({"success": False, "errors": ["Token expirado"]}),
                    401,
                )
            except jwt.InvalidTokenError:
                return (
                    jsonify({"success": False, "errors": ["Token inválido"]}),
                    401,
                )
            
            if claims.get("role") != "empresa":
                return (
                    jsonify({"success": False, "errors": ["Permiso de empresa requerido"]}),
                    401,
                )
            
            g.user_id = claims.get('sub')
            g.role = "empresa"
            g.empresa_id = g.user_id
            scope_error = _deny_cross_tenant_access(kwargs)
            if scope_error:
                return scope_error
            return f(*args, **kwargs)
            
        except Exception as e:
            # print(f"Error en require_empresa_token: {e}")
            return (
                jsonify({"success": False, "errors": ["Error de autenticación"]}),
                422,
            )
    return decorated_function


def require_empresa_or_admin_token(f):
    """Permite acceso tanto a empresa como a super_admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Intentar obtener el token de las cookies primero
            auth_token = request.cookies.get('auth_token')
            
            if not auth_token:
                # Si no hay cookie, intentar con header Authorization
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    auth_token = auth_header.replace('Bearer ', '')
                    # Verificar que no sea el placeholder 'cookie_auth'
                    if auth_token == 'cookie_auth':
                        auth_token = None
            
            if not auth_token:
                return (
                    jsonify({"success": False, "errors": ["Token de autenticación requerido"]}),
                    401,
                )
            
            # Decodificar el token manualmente
            try:
                claims = jwt.decode(
                    auth_token,
                    Config.JWT_SECRET_KEY,
                    algorithms=['HS256']
                )
            except jwt.ExpiredSignatureError:
                return (
                    jsonify({"success": False, "errors": ["Token expirado"]}),
                    401,
                )
            except jwt.InvalidTokenError:
                return (
                    jsonify({"success": False, "errors": ["Token inválido"]}),
                    401,
                )
            
            role = claims.get("role")
            if role in ["empresa", "super_admin"]:
                g.user_id = claims.get('sub')
                g.role = role
                if role == "empresa":
                    g.empresa_id = g.user_id
            else:
                return (
                    jsonify({"success": False, "errors": ["Permisos insuficientes"]}),
                    401,
                )
            scope_error = _deny_cross_tenant_access(kwargs)
            if scope_error:
                return scope_error
            return f(*args, **kwargs)
            
        except Exception as e:
            # print(f"Error en require_empresa_or_admin_token: {e}")
            return (
                jsonify({"success": False, "errors": ["Error de autenticación"]}),
                422,
            )
    return decorated_function
