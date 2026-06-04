from flask import jsonify, request

from models.alert_message import AlertMessage
from repositories.alert_message_repository import AlertMessageRepository
from repositories.mqtt_alert_repository import MqttAlertRepository


class AlertMessageController:
    """Controlador para mensajes WhatsApp asociados a alertas"""

    def __init__(self):
        self.repo = AlertMessageRepository()
        self.alert_repo = MqttAlertRepository()

    def log_message(self, alert_id):
        """POST /api/alerts/<alert_id>/messages - Registra un mensaje de la conversación de una alerta"""
        try:
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Formato inválido', 'message': 'JSON requerido'}), 400
            data = request.get_json() or {}

            direction = (data.get('direction') or '').strip().lower()
            if direction not in (AlertMessage.DIRECTION_IN, AlertMessage.DIRECTION_OUT):
                return jsonify({'success': False, 'error': 'direction debe ser in u out'}), 400

            phone = (data.get('phone') or '').strip()
            if not phone:
                return jsonify({'success': False, 'error': 'phone requerido'}), 400

            alert = self.alert_repo.get_alert_by_id(alert_id)
            if not alert:
                return jsonify({'success': False, 'error': 'Alerta no encontrada'}), 404

            message = AlertMessage(
                alert_id=alert._id,
                phone=phone,
                direction=direction,
                type=data.get('type', 'text'),
                body=data.get('body', ''),
                payload=data.get('payload', {}),
                user_id=data.get('user_id'),
                user_name=data.get('user_name'),
                is_template=bool(data.get('is_template', False)),
                is_navigation=bool(data.get('is_navigation', False))
            )
            created = self.repo.create(message)
            return jsonify({'success': True, 'message': created.to_json()}), 201
        except Exception as e:
            return jsonify({'success': False, 'error': 'Error interno', 'message': str(e)}), 500

    def list_messages(self, alert_id):
        """GET /api/alerts/<alert_id>/messages?direction=in&limit=15"""
        try:
            alert = self.alert_repo.get_alert_by_id(alert_id)
            if not alert:
                return jsonify({'success': False, 'error': 'Alerta no encontrada'}), 404

            direction = (request.args.get('direction') or '').strip().lower() or None
            if direction and direction not in (AlertMessage.DIRECTION_IN, AlertMessage.DIRECTION_OUT):
                direction = None

            try:
                limit = int(request.args.get('limit', 15))
            except ValueError:
                limit = 15
            limit = max(1, min(limit, 100))

            include_templates = (request.args.get('include_templates') or '').lower() == 'true'
            include_navigation = (request.args.get('include_navigation') or '').lower() == 'true'

            messages = self.repo.find_by_alert(
                alert_id=alert._id,
                direction=direction,
                limit=limit,
                include_templates=include_templates,
                include_navigation=include_navigation
            )
            return jsonify({
                'success': True,
                'alert_id': str(alert._id),
                'messages': [m.to_json() for m in messages]
            }), 200
        except Exception as e:
            return jsonify({'success': False, 'error': 'Error interno', 'message': str(e)}), 500
