from flask import request, jsonify, make_response
from services.auth_service import AuthService
from middleware.security_middleware import SecurityMiddleware
from flask_jwt_extended import decode_token

class AuthController:
    def __init__(self):
        self.auth_service = AuthService()
        self.security_middleware = SecurityMiddleware()

    def realtime_ticket(self):
        """Emitir un ticket temporal para el canal realtime autenticado."""
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
            from utils.realtime_token import create_realtime_ticket

            verify_jwt_in_request()
            user_id = get_jwt_identity()
            role = get_jwt().get('role')
            if role not in ('empresa', 'super_admin'):
                return jsonify({'success': False, 'error': 'Rol no autorizado'}), 403

            ticket, expires_at = create_realtime_ticket(user_id, role)
            return jsonify({
                'success': True,
                'ticket': ticket,
                'expires_at': expires_at,
            }), 200
        except Exception:
            return jsonify({
                'success': False,
                'error': 'No se pudo crear el ticket realtime',
            }), 401

    def validate_realtime_ticket(self):
        """Validacion interna usada una vez al abrir una conexion WebSocket."""
        from utils.realtime_token import verify_realtime_ticket

        data = request.get_json(silent=True) or {}
        principal = verify_realtime_ticket(data.get('ticket'))
        if not principal:
            return jsonify({'success': False}), 401
        return jsonify({'success': True, 'principal': principal}), 200

    def login(self):
        """Endpoint POST /auth/login"""
        try:
            data = request.get_json() or {}
            usuario = data.get('usuario')
            password = data.get('password')

            if not usuario or not password:
                return jsonify({'success': False, 'errors': ['Credenciales inválidas']}), 401

            # Preparar datos de la request para el sistema de sesiones
            request_data = {
                'remote_addr': request.environ.get('REMOTE_ADDR'),
                'user_agent': request.headers.get('User-Agent')
            }
            
            result = self.auth_service.login(usuario, password, request_data)

            if result['success']:
                # Crear respuesta exitosa con cookies seguras
                access_token = result['access_token']
                refresh_token = result['refresh_token']
                response_data = {
                    'success': True, 
                    'user': result['data'],
                    'message': 'Tokens enviados en cookies seguras'
                }
                
                response = make_response(jsonify(response_data), 200)
                
                # Decode access token to get JWT ID (jti)
                decoded_token = decode_token(access_token)
                jti = decoded_token.get('jti', None)
                
                # Create secure session record
                self.security_middleware.create_session_record(
                    user_id=result['data']['id'],
                    fingerprint=self.security_middleware.get_client_fingerprint(request),
                    jti=jti
                )
                
                # Configurar cookie de access token para desarrollo HTTP
                response.set_cookie(
                    'auth_token',
                    access_token,
                    max_age=15 * 60,       # 15 minutos en segundos
                    httponly=True,         # Cookie no accesible desde JavaScript
                    secure=False,          # False para desarrollo HTTP local
                    samesite='Lax',        # Lax para desarrollo HTTP local
                    domain=None,           # Solo para el dominio actual
                    path='/'               # Disponible en toda la aplicación
                )
                
                # Configurar cookie de refresh token para desarrollo HTTP
                response.set_cookie(
                    'refresh_token',
                    refresh_token,
                    max_age=7 * 24 * 60 * 60,  # 7 días en segundos
                    httponly=True,             # Cookie no accesible desde JavaScript
                    secure=False,              # False para desarrollo HTTP local
                    samesite='Lax',            # Lax para desarrollo HTTP local
                    domain=None,               # Solo para el dominio actual
                    path='/'                   # Disponible en toda la aplicación
                )
                
                return response
            return jsonify({'success': False, 'errors': result.get('errors', ['Credenciales inválidas'])}), 401
        except Exception as e:
            return jsonify({'success': False, 'errors': ['Error interno del servidor']}), 500
    
    def logout(self):
        """Endpoint POST /auth/logout"""
        try:
            # Obtener refresh token para invalidar la sesión
            refresh_token = request.cookies.get('refresh_token')
            
            # Invalidar sesión en base de datos si existe refresh token
            if refresh_token:
                logout_result = self.auth_service.logout(refresh_token)
                # Continuamos aunque falle el logout en DB
            
            response = make_response(jsonify({
                'success': True,
                'message': 'Sesión cerrada exitosamente'
            }), 200)
            
            # Limpiar cookies estableciendo expiración en el pasado
            response.set_cookie(
                'auth_token',
                '',
                max_age=0,
                httponly=True,
                secure=False,          # False para desarrollo HTTP local
                samesite='Lax',        # Lax para desarrollo HTTP local
                domain=None,
                path='/'
            )
            
            response.set_cookie(
                'refresh_token',
                '',
                max_age=0,
                httponly=True,
                secure=False,          # False para desarrollo HTTP local
                samesite='Lax',        # Lax para desarrollo HTTP local
                domain=None,
                path='/'
            )
            
            return response
            
        except Exception as e:
            return jsonify({'success': False, 'errors': ['Error interno del servidor']}), 500

    def refresh(self):
        """Endpoint POST /auth/refresh"""
        try:
            # Obtener refresh token desde cookie
            refresh_token = request.cookies.get('refresh_token')
            
            if not refresh_token:
                return jsonify({'success': False, 'errors': ['Refresh token faltante']}), 401
            
            # Preparar datos de la request para validación de sesión
            request_data = {
                'remote_addr': request.environ.get('REMOTE_ADDR'),
                'user_agent': request.headers.get('User-Agent')
            }
            
            # Generar nuevo access token
            result = self.auth_service.refresh_token(refresh_token, request_data)
            
            if result['success']:
                response_data = {
                    'success': True,
                    'message': 'Access token renovado exitosamente'
                }
                
                response = make_response(jsonify(response_data), 200)
                
                # Configurar nueva cookie de access token
                response.set_cookie(
                    'auth_token',
                    result['access_token'],
                    max_age=15 * 60,       # 15 minutos en segundos
                    httponly=True,         # Cookie no accesible desde JavaScript
                    secure=False,          # False para desarrollo HTTP local
                    samesite='Lax',        # Lax para desarrollo HTTP local
                    domain=None,           # Solo para el dominio actual
                    path='/'               # Disponible en toda la aplicación
                )
                
                return response
            
            return jsonify({'success': False, 'errors': result.get('errors', ['Refresh token inválido'])}), 401
            
        except Exception as e:
            return jsonify({'success': False, 'errors': ['Error interno del servidor']}), 500
    
    def get_my_sessions(self):
        """Endpoint GET /auth/sessions - Obtener sesiones activas del usuario actual"""
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            
            # Verificar que hay un token válido
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            if not user_id:
                return jsonify({'success': False, 'errors': ['Token inválido']}), 401
            
            # Obtener sesiones activas
            result = self.auth_service.get_user_sessions(user_id)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'data': result['data'],
                    'count': result['count']
                }), 200
            else:
                return jsonify(result), 500
                
        except Exception as e:
            return jsonify({'success': False, 'errors': ['Error interno del servidor']}), 500
    
    def logout_session(self, session_id):
        """Endpoint DELETE /auth/sessions/<session_id> - Cerrar sesión específica"""
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            
            # Verificar que hay un token válido
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            if not user_id:
                return jsonify({'success': False, 'errors': ['Token inválido']}), 401
            
            # Invalidar sesión específica
            result = self.auth_service.invalidate_session(session_id=session_id)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Sesión cerrada exitosamente'
                }), 200
            else:
                return jsonify(result), 404
                
        except Exception as e:
            return jsonify({'success': False, 'errors': ['Error interno del servidor']}), 500
    
    def logout_all_sessions(self):
        """Endpoint POST /auth/logout-all - Cerrar todas las sesiones del usuario"""
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
            
            # Verificar que hay un token válido
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            current_jti = get_jwt().get('jti')
            
            if not user_id:
                return jsonify({'success': False, 'errors': ['Token inválido']}), 401
            
            # Cerrar todas las sesiones excepto la actual (opcional)
            data = request.get_json() or {}
            keep_current = data.get('keep_current', False)
            keep_current_jti = current_jti if keep_current else None
            
            result = self.auth_service.logout_all_sessions(user_id, keep_current_jti)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': f"{result.get('invalidated_count', 0)} sesiones cerradas",
                    'invalidated_count': result.get('invalidated_count', 0)
                }), 200
            else:
                return jsonify(result), 500
                
        except Exception as e:
            return jsonify({'success': False, 'errors': ['Error interno del servidor']}), 500
