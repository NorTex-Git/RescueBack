from flask import Blueprint
from controllers.empresa_controller import EmpresaController
from controllers.admin_controller import AdminController
from controllers.auth_controller import AuthController
from controllers.hardware_controller import HardwareController
from controllers.hardware_type_controller import HardwareTypeController
from controllers.tipo_empresa_controller import tipo_empresa_controller
from controllers.tipo_alarma_controller import tipo_alarma_bp
from controllers.super_admin_dashboard_controller import SuperAdminDashboardController
from utils.permissions import (
    require_empresa_or_admin_token,
    require_empresa_token,
    require_super_admin_token,
)
from decorators.internal_token_decorator import require_internal_token

# ========== BLUEPRINT DE AUTENTICACIÓN ==========
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
auth_controller = AuthController()

@auth_bp.route('/login', methods=['POST'])
def login():
    """POST /auth/login - Iniciar sesión"""
    return auth_controller.login()

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """POST /auth/logout - Cerrar sesión"""
    return auth_controller.logout()

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """POST /auth/refresh - Renovar access token"""
    return auth_controller.refresh()

@auth_bp.route('/realtime-ticket', methods=['GET'])
def realtime_ticket():
    """GET /auth/realtime-ticket - Ticket efimero para WebSocket."""
    return auth_controller.realtime_ticket()

@auth_bp.route('/realtime-ticket/validate', methods=['POST'])
@require_internal_token
def validate_realtime_ticket():
    """POST interno para que el gateway valide el ticket sin compartir secretos."""
    return auth_controller.validate_realtime_ticket()

@auth_bp.route('/sessions', methods=['GET'])
def get_my_sessions():
    """GET /auth/sessions - Obtener sesiones activas del usuario actual"""
    return auth_controller.get_my_sessions()

@auth_bp.route('/sessions/<session_id>', methods=['DELETE'])
def logout_session(session_id):
    """DELETE /auth/sessions/<session_id> - Cerrar sesión específica"""
    return auth_controller.logout_session(session_id)

@auth_bp.route('/logout-all', methods=['POST'])
def logout_all_sessions():
    """POST /auth/logout-all - Cerrar todas las sesiones del usuario"""
    return auth_controller.logout_all_sessions()

# ========== BLUEPRINT DE EMPRESAS ==========
empresa_bp = Blueprint('empresas', __name__, url_prefix='/api/empresas')
empresa_controller = EmpresaController()

@empresa_bp.route('/', methods=['POST'])
def create_empresa():
    """POST /api/empresas - Crear empresa (solo super admin)"""
    return empresa_controller.create_empresa()

@empresa_bp.route('/', methods=['GET'])
def get_all_empresas():
    """GET /api/empresas - Obtener todas las empresas activas (para formularios)"""
    return empresa_controller.get_all_empresas()

@empresa_bp.route('/dashboard/all', methods=['GET'])
def get_all_empresas_dashboard():
    """GET /api/empresas/dashboard/all - Obtener TODAS las empresas (activas e inactivas) para dashboards"""
    return empresa_controller.get_all_empresas_dashboard()

@empresa_bp.route('/<empresa_id>', methods=['GET'])
def get_empresa(empresa_id):
    """GET /api/empresas/<id> - Obtener empresa por ID"""
    return empresa_controller.get_empresa(empresa_id)

@empresa_bp.route('/<empresa_id>', methods=['PUT'])
def update_empresa(empresa_id):
    """PUT /api/empresas/<id> - Actualizar empresa (solo el creador)"""
    return empresa_controller.update_empresa(empresa_id)

@empresa_bp.route('/<empresa_id>', methods=['DELETE'])
def delete_empresa(empresa_id):
    """DELETE /api/empresas/<id> - Eliminar empresa (solo el creador)"""
    return empresa_controller.delete_empresa(empresa_id)

@empresa_bp.route('/mis-empresas', methods=['GET'])
def get_my_empresas():
    """GET /api/empresas/mis-empresas - Obtener empresas del super admin autenticado"""
    return empresa_controller.get_my_empresas()

@empresa_bp.route('/buscar-por-ubicacion', methods=['GET'])
def search_by_ubicacion():
    """GET /api/empresas/buscar-por-ubicacion?ubicacion=<ubicacion> - Buscar por ubicación"""
    return empresa_controller.search_empresas_by_ubicacion()

@empresa_bp.route('/estadisticas', methods=['GET'])
def get_stats():
    """GET /api/empresas/estadisticas - Obtener estadísticas (solo super admin)"""
    return empresa_controller.get_empresa_stats()

@empresa_bp.route('/<empresa_id>/including-inactive', methods=['GET'])
def get_empresa_including_inactive(empresa_id):
    """GET /api/empresas/<id>/including-inactive - Obtener empresa incluyendo inactivas (solo super admin)"""
    return empresa_controller.get_empresa_including_inactive(empresa_id)

@empresa_bp.route('/<empresa_id>/toggle-status', methods=['PATCH'])
def toggle_empresa_status(empresa_id):
    """PATCH /api/empresas/<id>/toggle-status - Activar/desactivar empresa (solo super admin)"""
    return empresa_controller.toggle_empresa_status(empresa_id)

@empresa_bp.route('/<empresa_id>/statistics', methods=['GET'])
@require_empresa_or_admin_token
def get_empresa_statistics(empresa_id):
    """GET /api/empresas/<id>/statistics - Obtener estadísticas de una empresa específica"""
    return empresa_controller.get_empresa_statistics(empresa_id)

@empresa_bp.route('/<empresa_id>/activity', methods=['GET'])
def empresa_activity(empresa_id):
    return admin_controller.get_empresa_activity(empresa_id)

# ========== BLUEPRINT DE ADMIN ==========
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
admin_controller = AdminController()

# ========== BLUEPRINT DE HARDWARE ==========
hardware_bp = Blueprint('hardware', __name__, url_prefix='/api/hardware')
hardware_controller = HardwareController()
hardware_type_bp = Blueprint('hardware_types', __name__, url_prefix='/api/hardware-types')
hardware_type_controller = HardwareTypeController()

@hardware_bp.route('/', methods=['POST'])
def create_hardware():
    return hardware_controller.create_hardware()

@hardware_bp.route('/', methods=['GET'])
def get_hardware_list():
    return hardware_controller.get_hardware_list()

@hardware_bp.route('/empresa/<empresa_id>', methods=['GET'])
@require_empresa_or_admin_token
def get_hardware_by_empresa(empresa_id):
    return hardware_controller.get_hardware_by_empresa(empresa_id)

@hardware_bp.route('/<hardware_id>', methods=['GET'])
def get_hardware(hardware_id):
    return hardware_controller.get_hardware(hardware_id)

@hardware_bp.route('/<hardware_id>/direccion-url', methods=['GET'])
@require_empresa_or_admin_token
def get_hardware_direccion_url(hardware_id):
    """GET /api/hardware/<id>/direccion-url - Obtener URL de la dirección del hardware"""
    return hardware_controller.get_hardware_direccion_url(hardware_id)

@hardware_bp.route('/<hardware_id>', methods=['PUT'])
def update_hardware(hardware_id):
    return hardware_controller.update_hardware(hardware_id)

@hardware_bp.route('/<hardware_id>', methods=['DELETE'])
def delete_hardware(hardware_id):
    return hardware_controller.delete_hardware(hardware_id)

@hardware_bp.route('/<hardware_id>/toggle-status', methods=['PATCH'])
def toggle_hardware_status(hardware_id):
    """PATCH /api/hardware/<id>/toggle-status - Activar/desactivar hardware"""
    return hardware_controller.toggle_hardware_status(hardware_id)

@hardware_bp.route('/physical-status', methods=['PUT'])
def update_physical_status_by_topic():
    """PUT /api/hardware/physical-status - Actualizar physical_status por empresa y hardware (token interno)"""
    return hardware_controller.update_physical_status_by_topic()

@hardware_bp.route('/physical-status/check', methods=['POST'])
def check_physical_status_stale():
    """POST /api/hardware/physical-status/check - Marcar hardware con status vencido"""
    return hardware_controller.check_physical_status_stale()

@hardware_bp.route('/all-including-inactive', methods=['GET'])
def get_all_hardware_including_inactive():
    """GET /api/hardware/all-including-inactive - Obtener todos los hardware incluyendo inactivos"""
    return hardware_controller.get_all_hardware_including_inactive()

@hardware_bp.route('/empresa/<empresa_id>/including-inactive', methods=['GET'])
@require_empresa_or_admin_token
def get_hardware_by_empresa_including_inactive(empresa_id):
    """GET /api/hardware/empresa/<empresa_id>/including-inactive - Obtener hardware de empresa incluyendo inactivos"""
    return hardware_controller.get_hardware_by_empresa_including_inactive(empresa_id)

# ========== BLUEPRINT DE TIPOS DE HARDWARE ==========
@hardware_type_bp.route('/', methods=['POST'])
def create_hardware_type():
    return hardware_type_controller.create_type()

@hardware_type_bp.route('/', methods=['GET'])
def get_hardware_types():
    return hardware_type_controller.get_types()

@hardware_type_bp.route('/<type_id>', methods=['GET'])
def get_hardware_type(type_id):
    return hardware_type_controller.get_type(type_id)

@hardware_type_bp.route('/<type_id>', methods=['PUT'])
def update_hardware_type(type_id):
    return hardware_type_controller.update_type(type_id)

@hardware_type_bp.route('/<type_id>', methods=['DELETE'])
def delete_hardware_type(type_id):
    return hardware_type_controller.delete_type(type_id)

@admin_bp.route('/activity', methods=['GET'])
def get_admin_activity():
    return admin_controller.get_activity()

@admin_bp.route('/activity-admin', methods=['GET'])
def get_admin_activity_only():
    return admin_controller.get_activity_admin_only()

@admin_bp.route('/distribution', methods=['GET'])
def get_admin_distribution():
    return admin_controller.get_distribution()

# ========== BLUEPRINT DE SUPER ADMIN DASHBOARD ==========
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')
dashboard_controller = SuperAdminDashboardController()

@dashboard_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """GET /api/dashboard/stats - Estadísticas generales del sistema"""
    return dashboard_controller.get_dashboard_stats()

@dashboard_bp.route('/recent-companies', methods=['GET'])
def get_recent_companies():
    """GET /api/dashboard/recent-companies - Empresas recientes"""
    return dashboard_controller.get_recent_companies()

@dashboard_bp.route('/recent-users', methods=['GET'])
def get_recent_users():
    """GET /api/dashboard/recent-users - Usuarios recientes"""
    return dashboard_controller.get_recent_users()

@dashboard_bp.route('/activity-chart', methods=['GET'])
def get_activity_chart():
    """GET /api/dashboard/activity-chart - Datos para gráfico de actividad"""
    return dashboard_controller.get_activity_chart()

@dashboard_bp.route('/distribution-chart', methods=['GET'])
def get_distribution_chart():
    """GET /api/dashboard/distribution-chart - Datos para gráfico de distribución"""
    return dashboard_controller.get_distribution_chart()

@dashboard_bp.route('/hardware-stats', methods=['GET'])
def get_hardware_stats():
    """GET /api/dashboard/hardware-stats - Estadísticas de hardware"""
    return dashboard_controller.get_hardware_stats()

@dashboard_bp.route('/system-performance', methods=['GET'])
def get_system_performance():
    """GET /api/dashboard/system-performance - Rendimiento del sistema"""
    return dashboard_controller.get_system_performance()
# ========== BLUEPRINT DE MULTI-TENANT (USUARIOS POR EMPRESA) ==========
from controllers.multitenant_controller import MultiTenantController
from controllers.mqtt_alert_controller import MqttAlertController

multitenant_bp = Blueprint('multitenant', __name__, url_prefix='/empresas')
multitenant_controller = MultiTenantController()

@multitenant_bp.route('/<empresa_id>/usuarios', methods=['POST'])
@require_empresa_or_admin_token
def create_usuario_for_empresa(empresa_id):
    """POST /empresas/<empresa_id>/usuarios - Crear usuario para empresa específica"""
    return multitenant_controller.create_usuario_for_empresa(empresa_id)

@multitenant_bp.route('/<empresa_id>/usuarios', methods=['GET'])
@require_empresa_or_admin_token
def get_usuarios_for_empresa(empresa_id):
    """GET /empresas/<empresa_id>/usuarios - Obtener usuarios para empresa específica"""
    return multitenant_controller.get_usuarios_by_empresa(empresa_id)

@multitenant_bp.route('/<empresa_id>/usuarios/<usuario_id>', methods=['GET'])
@require_empresa_or_admin_token
def get_usuario_by_empresa(empresa_id, usuario_id):
    """GET /empresas/<empresa_id>/usuarios/<usuario_id> - Obtener usuario específico"""
    return multitenant_controller.get_usuario_by_empresa(empresa_id, usuario_id)

@multitenant_bp.route('/<empresa_id>/usuarios/<usuario_id>', methods=['PUT'])
@require_empresa_or_admin_token
def update_usuario_by_empresa(empresa_id, usuario_id):
    """PUT /empresas/<empresa_id>/usuarios/<usuario_id> - Actualizar usuario"""
    return multitenant_controller.update_usuario_by_empresa(empresa_id, usuario_id)

@multitenant_bp.route('/<empresa_id>/usuarios/<usuario_id>', methods=['DELETE'])
@require_super_admin_token
def delete_usuario_by_empresa(empresa_id, usuario_id):
    """DELETE /empresas/<empresa_id>/usuarios/<usuario_id> - Eliminar usuario"""
    return multitenant_controller.delete_usuario_by_empresa(empresa_id, usuario_id)

@multitenant_bp.route('/<empresa_id>/usuarios/<usuario_id>/toggle-status', methods=['PATCH'])
@require_empresa_or_admin_token
def toggle_usuario_status(empresa_id, usuario_id):
    """PATCH /empresas/<empresa_id>/usuarios/<usuario_id>/toggle-status - Activar/desactivar usuario"""
    return multitenant_controller.toggle_usuario_status(empresa_id, usuario_id)

@multitenant_bp.route('/<empresa_id>/usuarios/including-inactive', methods=['GET'])
@require_empresa_or_admin_token
def get_usuarios_by_empresa_including_inactive(empresa_id):
    """GET /empresas/<empresa_id>/usuarios/including-inactive - Obtener usuarios incluyendo inactivos"""
    
    return multitenant_controller.get_usuarios_by_empresa_including_inactive(empresa_id)

# ========== BLUEPRINT DE ALERTAS MQTT - COMENTADO PARA REHACER ==========
mqtt_alert_bp = Blueprint('mqtt_alerts', __name__, url_prefix='/api/mqtt-alerts')
mqtt_alert_controller = MqttAlertController()

# Carga inicial y reconciliacion del panel. Los cambios posteriores llegan por
# realtime, por lo que este endpoint no debe consultarse mediante polling corto.
notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notifications_bp.route('/active', methods=['GET'])
@require_empresa_or_admin_token
def get_active_notifications():
    from flask import g, jsonify, request

    page = max(int(request.args.get('page', 1)), 1)
    limit = min(max(int(request.args.get('limit', 10)), 1), 50)
    if g.role == 'empresa':
        result = mqtt_alert_controller.service.get_alerts_active_by_empresa_sede(
            g.empresa_id, page, limit
        )
    else:
        result = mqtt_alert_controller.service.get_active_alerts(page, limit)

    alerts = result.get('alerts') or result.get('data') or []
    pagination = result.get('pagination') or {}
    return jsonify({
        'success': bool(result.get('success', True)),
        'notifications': alerts,
        'total': result.get('total', pagination.get('total_items', len(alerts))),
    }), 200

# ========== BLUEPRINT DE AUTENTICACIÓN DE HARDWARE ==========
from controllers.hardware_auth_controller import HardwareAuthController
hardware_auth_bp = Blueprint('hardware_auth', __name__, url_prefix='/api/hardware-auth')
hardware_auth_controller = HardwareAuthController()

@hardware_auth_bp.route('/authenticate', methods=['POST'])
def authenticate_hardware():
    """POST /api/hardware-auth/authenticate - SOLO autenticación de hardware"""
    return hardware_auth_controller.authenticate_hardware()

# ========== RUTAS MQTT ALERTS CRUD ==========
from decorators.hardware_auth_decorator import require_hardware_token

# Ruta para procesar mensajes MQTT (SOLO token de hardware)
@mqtt_alert_bp.route('/process', methods=['POST'])
@require_hardware_token  # Solo token de hardware
def process_mqtt_message():
    """POST /api/mqtt-alerts/process - Procesar mensaje MQTT (Solo token de hardware)"""
    return mqtt_alert_controller.process_mqtt_message()

# Ruta para crear alertas manualmente (SOLO token de hardware)
@mqtt_alert_bp.route('/', methods=['POST'])
@require_hardware_token  # Solo token de hardware
def create_alert():
    """POST /api/mqtt-alerts - Crear nueva alerta (Solo token de hardware)"""
    return mqtt_alert_controller.create_alert()

# Rutas de lectura (requieren autenticación general)
@mqtt_alert_bp.route('/', methods=['GET'])
@require_empresa_or_admin_token
def get_alerts():
    """GET /api/mqtt-alerts - Obtener todas las alertas"""
    return mqtt_alert_controller.get_alerts()

@mqtt_alert_bp.route('/<alert_id>', methods=['GET'])
@require_empresa_or_admin_token
def get_alert_by_id(alert_id):
    """GET /api/mqtt-alerts/<alert_id> - Obtener alerta por ID"""
    return mqtt_alert_controller.get_alert_by_id(alert_id)

# Rutas de actualización y eliminación (requieren autenticación general)
@mqtt_alert_bp.route('/<alert_id>', methods=['PUT'])
@require_empresa_or_admin_token
def update_alert(alert_id):
    """PUT /api/mqtt-alerts/<alert_id> - Actualizar alerta"""
    return mqtt_alert_controller.update_alert(alert_id)

@mqtt_alert_bp.route('/<alert_id>', methods=['DELETE'])
@require_empresa_or_admin_token
def delete_alert(alert_id):
    """DELETE /api/mqtt-alerts/<alert_id> - Eliminar alerta"""
    return mqtt_alert_controller.delete_alert(alert_id)

# Rutas especiales
@mqtt_alert_bp.route('/<alert_id>/authorize', methods=['PATCH'])
@require_empresa_or_admin_token
def authorize_alert(alert_id):
    """PATCH /api/mqtt-alerts/<alert_id>/authorize - Autorizar alerta"""
    return mqtt_alert_controller.authorize_alert(alert_id)

@mqtt_alert_bp.route('/<alert_id>/toggle-status', methods=['PATCH'])
@require_empresa_or_admin_token
def toggle_alert_status(alert_id):
    """PATCH /api/mqtt-alerts/<alert_id>/toggle-status - Alternar estado activo"""
    return mqtt_alert_controller.toggle_alert_status(alert_id)

# Rutas de consulta específicas
@mqtt_alert_bp.route('/empresa/<empresa_id>', methods=['GET'])
@require_empresa_or_admin_token
def get_alerts_by_empresa(empresa_id):
    """GET /api/mqtt-alerts/empresa/<empresa_id> - Obtener alertas por empresa"""
    return mqtt_alert_controller.get_alerts_by_empresa(empresa_id)

@mqtt_alert_bp.route('/active', methods=['GET'])
@require_empresa_or_admin_token
def get_active_alerts():
    """GET /api/mqtt-alerts/active - Obtener alertas activas"""
    return mqtt_alert_controller.get_active_alerts()

@mqtt_alert_bp.route('/unauthorized', methods=['GET'])
@require_empresa_or_admin_token
def get_unauthorized_alerts():
    """GET /api/mqtt-alerts/unauthorized - Obtener alertas no autorizadas"""
    return mqtt_alert_controller.get_unauthorized_alerts()

@mqtt_alert_bp.route('/inactive', methods=['GET'])
@require_empresa_token
def get_inactive_alerts():
    """GET /api/mqtt-alerts/inactive - Obtener alertas inactivas/desactivadas"""
    return mqtt_alert_controller.get_inactive_alerts()

@mqtt_alert_bp.route('/stats', methods=['GET'])
@require_empresa_or_admin_token
def get_alerts_stats():
    """GET /api/mqtt-alerts/stats - Obtener estadísticas de alertas"""
    return mqtt_alert_controller.get_alerts_stats()

@mqtt_alert_bp.route('/update-user-status', methods=['PATCH'])
def update_alert_user_status():
    """PATCH /api/mqtt-alerts/update-user-status - Actualizar estado de usuario en alerta (SIN AUTENTICACIÓN)"""
    return mqtt_alert_controller.update_alert_user_status()

@mqtt_alert_bp.route('/empresa/<empresa_id>/active-by-sede', methods=['GET'])
@require_empresa_token
def get_active_alerts_by_empresa_sede(empresa_id):
    """GET /api/mqtt-alerts/empresa/{empresaId}/active-by-sede - Obtener alertas activas por empresa y sede con paginación"""
    return mqtt_alert_controller.get_active_alerts_by_empresa_sede(empresa_id)

# Rutas de utilidad y verificación
@mqtt_alert_bp.route('/verify-empresa-sede', methods=['GET'])
@require_empresa_or_admin_token
def verify_empresa_sede():
    """GET /api/mqtt-alerts/verify-empresa-sede?empresa_nombre=X&sede=Y - Verificar empresa y sede"""
    return mqtt_alert_controller.verify_empresa_sede()

@mqtt_alert_bp.route('/test-flow', methods=['GET'])
def test_complete_flow():
    """GET /api/mqtt-alerts/test-flow - Probar flujo completo con campo data (Público para pruebas)"""
    return mqtt_alert_controller.test_complete_flow()

@mqtt_alert_bp.route('/verify-hardware', methods=['GET'])
@require_empresa_or_admin_token
def verify_hardware():
    """GET /api/mqtt-alerts/verify-hardware?hardware_nombre=X - Verificar hardware"""
    return mqtt_alert_controller.verify_hardware()

# Ruta para crear alerta de usuario SIN AUTENTICACIÓN
@mqtt_alert_bp.route('/user-alert', methods=['POST'])
def create_user_alert():
    """POST /api/mqtt-alerts/user-alert - Crear alerta de usuario con solo teléfono (SIN AUTENTICACIÓN)"""
    return mqtt_alert_controller.create_user_alert()

# Ruta para desactivar alerta SIN AUTENTICACIÓN
@mqtt_alert_bp.route('/user-alert/deactivate', methods=['PUT'])
def deactivate_user_alert():
    """PUT /api/mqtt-alerts/user-alert/deactivate - Desactivar alerta con ID en body y tipo de quien desactiva (SIN AUTENTICACIÓN)"""
    return mqtt_alert_controller.deactivate_alert_from_body()

# Ruta para obtener alerta específica para un usuario SIN AUTENTICACIÓN
@mqtt_alert_bp.route('/user-alert/details', methods=['POST'])
def get_alert_details_for_user():
    """POST /api/mqtt-alerts/user-alert/details - Obtener detalles de una alerta si el usuario tiene acceso (SIN AUTENTICACIÓN)"""
    return mqtt_alert_controller.get_alert_details_for_user()

# Rutas para Alert Managers (SIN AUTENTICACIÓN - usadas por WhatsApp/MqttConnection)
@mqtt_alert_bp.route('/manager/active-by-sede', methods=['POST'])
def manager_list_active_by_sede():
    """POST /api/mqtt-alerts/manager/active-by-sede - Listar última alerta activa por sede para manager"""
    return mqtt_alert_controller.manager_list_active_by_sede()

@mqtt_alert_bp.route('/manager/switch-focus', methods=['POST'])
def manager_switch_focus():
    """POST /api/mqtt-alerts/manager/switch-focus - Cambiar alerta en foco de un manager (actualiza cache WhatsApp)"""
    return mqtt_alert_controller.manager_switch_focus()

# Rutas para mensajes asociados a alertas (auditoría + resumen)
from controllers.alert_message_controller import AlertMessageController
alert_message_controller = AlertMessageController()

@mqtt_alert_bp.route('/<alert_id>/messages', methods=['POST'])
def log_alert_message(alert_id):
    """POST /api/mqtt-alerts/<alert_id>/messages - Registrar mensaje de la conversación (in/out)"""
    return alert_message_controller.log_message(alert_id)

@mqtt_alert_bp.route('/<alert_id>/messages', methods=['GET'])
def list_alert_messages(alert_id):
    """GET /api/mqtt-alerts/<alert_id>/messages?direction=in&limit=15 - Listar mensajes de la alerta"""
    return alert_message_controller.list_messages(alert_id)

# ========== BLUEPRINT DE BÚSQUEDA POR TELÉFONO ==========
from controllers.phone_lookup_controller import PhoneLookupController
phone_lookup_bp = Blueprint('phone_lookup', __name__, url_prefix='/api/phone-lookup')
phone_lookup_controller = PhoneLookupController()

@phone_lookup_bp.route('/', methods=['GET'])
def lookup_by_phone():
    """GET /api/phone-lookup?telefono=NUMERO - Buscar información por número de teléfono"""
    return phone_lookup_controller.lookup_by_phone()

# ========== BLUEPRINT DE CONTACTO ==========
from controllers.contact_controller import ContactController
contact_bp = Blueprint('contact', __name__, url_prefix='/api/contact')
contact_controller = ContactController()

@contact_bp.route('/send', methods=['POST'])
def send_contact_email():
    """POST /api/contact/send - Enviar formulario de contacto via email"""
    return contact_controller.send_contact_email()

@contact_bp.route('/', methods=['GET'])
def get_contacts():
    """GET /api/contact - Obtener lista de contactos (para administración)"""
    return contact_controller.get_contacts()

@contact_bp.route('/<contact_id>', methods=['GET'])
def get_contact_by_id(contact_id):
    """GET /api/contact/<contact_id> - Obtener contacto específico por ID"""
    return contact_controller.get_contact_by_id(contact_id)

@contact_bp.route('/status/<status>', methods=['GET'])
def get_contacts_by_status(status):
    """GET /api/contact/status/<status> - Obtener contactos por status"""
    return contact_controller.get_contacts_by_status(status)

# ========== FUNCIÓN PARA REGISTRAR TODAS LAS RUTAS ==========
def register_routes(app):
    """Registra todos los blueprints en la aplicación Flask"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(empresa_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(hardware_bp)
    app.register_blueprint(hardware_type_bp)
    app.register_blueprint(multitenant_bp)
    app.register_blueprint(mqtt_alert_bp)  # Rehabilitado para manejar alertas MQTT
    app.register_blueprint(notifications_bp)
    app.register_blueprint(hardware_auth_bp)
    app.register_blueprint(phone_lookup_bp)  # Búsqueda por teléfono
    app.register_blueprint(contact_bp)  # Formulario de contacto
    app.register_blueprint(tipo_alarma_bp, url_prefix='/api')
    app.register_blueprint(tipo_empresa_controller, url_prefix='/api')
