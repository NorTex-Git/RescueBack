import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv('MONGO_URI')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'rescue')
    SECRET_KEY = os.getenv('SECRET_KEY')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    PORT = int(os.getenv('PORT', 5000))
    INTERNAL_TOKEN = os.getenv('INTERNAL_TOKEN')
    INTERNAL_TOKEN_HEADER = os.getenv('INTERNAL_TOKEN_HEADER', 'X-Internal-Token')
    HARDWARE_STATUS_DEFAULT_EXCLUDED_TYPES = os.getenv('HARDWARE_STATUS_DEFAULT_EXCLUDED_TYPES', '')
    
    # Validar variables de entorno críticas
    @classmethod
    def validate_config(cls):
        required_vars = ['MONGO_URI', 'SECRET_KEY', 'JWT_SECRET_KEY']
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var, None):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Variables de entorno faltantes: {', '.join(missing_vars)}. Verifica tu archivo .env")
    
    # Configuración de cookies JWT para comunicación Docker interna
    JWT_TOKEN_LOCATION = ['cookies', 'headers']  # Permitir tanto cookies como headers
    JWT_COOKIE_SECURE = True  # True para HTTPS (frontend expuesto por Cloudflare)
    JWT_COOKIE_HTTPONLY = True  # HttpOnly para seguridad
    JWT_COOKIE_SAMESITE = 'Lax'  # Lax para producción (más seguro que None)
    JWT_COOKIE_CSRF_PROTECT = False  # Desactivamos CSRF protection
    
    # Configuración de Access Token
    JWT_ACCESS_COOKIE_NAME = 'auth_token'  # Nombre de la cookie de access token
    JWT_ACCESS_TOKEN_EXPIRES = 15 * 60  # 15 minutos para access token (900 segundos)
    
    # Configuración de Refresh Token
    JWT_REFRESH_COOKIE_NAME = 'refresh_token'  # Nombre de la cookie de refresh token
    JWT_REFRESH_TOKEN_EXPIRES = 7 * 24 * 60 * 60  # 7 días para refresh token
    
    # Configuración del servicio de WhatsApp
    WHATSAPP_SERVICE_URL = os.getenv('WHATSAPP_SERVICE_URL', 'http://localhost:5050/api')
    WHATSAPP_SERVICE_TIMEOUT = int(os.getenv('WHATSAPP_SERVICE_TIMEOUT', 30))

    # URL interna del servicio MQTT/WebSocket para fanout
    MQTT_SERVICE_URL = os.getenv('MQTT_SERVICE_URL', 'http://rescue-websocket:8081')
    MQTT_SERVICE_TIMEOUT = int(os.getenv('MQTT_SERVICE_TIMEOUT', 10))
    # Secreto compartido para tickets efimeros del canal realtime.
    REALTIME_SECRET = os.getenv('REALTIME_SECRET') or JWT_SECRET_KEY
    REALTIME_TICKET_TTL_SECONDS = int(os.getenv('REALTIME_TICKET_TTL_SECONDS', 60))
