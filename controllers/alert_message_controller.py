import requests
from flask import Response, jsonify, request

from core.config import Config
from models.alert_message import AlertMessage
from repositories.alert_media_repository import AlertMediaRepository
from repositories.alert_message_repository import AlertMessageRepository
from repositories.empresa_repository import EmpresaRepository
from repositories.mqtt_alert_repository import MqttAlertRepository
from utils.realtime_publisher import publish_realtime_event
from utils.whatsapp_service_client import whatsapp_client

# Tipos de media que descargamos y mostramos en el chat (documentos NO).
SUPPORTED_MEDIA_TYPES = {'image', 'audio', 'video', 'sticker'}
# Límite defensivo de tamaño (25 MB) para no guardar binarios enormes.
MAX_MEDIA_BYTES = 25 * 1024 * 1024


class AlertMessageController:
    """Controlador para mensajes WhatsApp asociados a alertas"""

    def __init__(self):
        self.repo = AlertMessageRepository()
        self.alert_repo = MqttAlertRepository()
        self.media_repo = AlertMediaRepository()

    def _resolve_media(self, msg_type, payload):
        """Descarga la media de WhatsApp (vía WebHook) y la guarda en GridFS.

        Devuelve (media_url, mime_type) o (None, None) si no aplica o falla.
        El `payload` es el `entry` crudo de WhatsApp: `payload[msg_type]` trae
        `{id, mime_type, ...}` para image/audio/video/sticker.
        """
        if msg_type not in SUPPORTED_MEDIA_TYPES or not isinstance(payload, dict):
            return None, None
        media_info = payload.get(msg_type)
        if not isinstance(media_info, dict):
            return None, None
        media_id = media_info.get('id')
        if not media_id:
            return None, None
        try:
            base = Config.WHATSAPP_SERVICE_URL.rstrip('/')
            response = requests.get(f"{base}/media/{media_id}/download", timeout=60, stream=True)
            if response.status_code != 200:
                return None, None
            content = response.content
            if not content or len(content) > MAX_MEDIA_BYTES:
                return None, None
            mime_type = (
                media_info.get('mime_type')
                or response.headers.get('Content-Type')
                or 'application/octet-stream'
            )
            file_id = self.media_repo.store(
                content,
                filename=str(media_id),
                content_type=mime_type,
                metadata={'whatsapp_media_id': media_id, 'type': msg_type},
            )
            return f"/api/mqtt-alerts/media/{file_id}", mime_type
        except Exception:
            return None, None

    # Etiquetas de la cita cuando el mensaje respondido no tiene texto.
    MEDIA_LABELS = {
        'image': '📷 Imagen', 'audio': '🎵 Audio', 'video': '🎬 Video',
        'sticker': 'Sticker', 'document': '📎 Documento',
    }

    @staticmethod
    def _digits(value):
        return ''.join(ch for ch in str(value or '') if ch.isdigit())

    def _context_for_recipient(self, quoted, numero):
        """wamid válido para citar `quoted` en la conversación 1:1 de `numero`.

        Cada miembro tiene su propia copia (WhatsApp es 1:1):
        - El autor de un mensaje entrante tiene el wamid principal (`quoted.phone`).
        - El resto tiene su copia reenviada / recibida en `wa_recipients`.
        Devuelve None si `numero` no posee ese mensaje (se envía sin cita para no fallar).
        """
        if not quoted:
            return None
        target = self._digits(numero)
        if quoted.direction == AlertMessage.DIRECTION_IN and self._digits(quoted.phone) == target:
            return quoted.wa_message_id
        for rec in (quoted.wa_recipients or []):
            if self._digits(rec.get('phone')) == target:
                return rec.get('wa_message_id')
        return None

    @staticmethod
    def _extract_wamid(send_result):
        """Extrae el wamid saliente de la respuesta de WhatsApp (data.messages[0].id)."""
        try:
            return send_result['data']['messages'][0]['id']
        except (KeyError, IndexError, TypeError):
            return None

    def _build_reply_preview(self, msg):
        """Cita denormalizada (autor + snippet) del mensaje respondido, o None."""
        if not msg:
            return None
        body = (msg.body or '').strip() or self.MEDIA_LABELS.get(msg.type, f'[{msg.type}]')
        return {
            'message_id': str(msg._id),
            'wa_message_id': msg.wa_message_id,
            'author': msg.user_name or msg.phone or '',
            'snippet': body[:120],
            'type': msg.type,
        }

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
            # Rechazar logs sobre alertas ya desactivadas: previene mensajes huérfanos
            # cuando manager sigue escribiendo después del cierre.
            if hasattr(alert, 'activo') and not alert.activo:
                return jsonify({'success': False, 'error': 'Alerta inactiva', 'message': 'No se pueden registrar mensajes en una alerta desactivada'}), 409

            msg_type = data.get('type', 'text')
            payload = data.get('payload') or {}
            # Descargar y guardar la media (imagen/audio/video/sticker) para poder
            # mostrarla en el panel; documentos y texto no pasan por aquí.
            media_url, mime_type = self._resolve_media(msg_type, payload)

            # Threading: wamid propio y, si es respuesta, cita del mensaje respondido.
            wa_message_id = payload.get('id') if isinstance(payload, dict) else None
            reply_to = None
            context = payload.get('context') if isinstance(payload, dict) else None
            if isinstance(context, dict) and context.get('id'):
                quoted = self.repo.find_by_wa_id(alert._id, context.get('id'))
                reply_to = self._build_reply_preview(quoted)

            message = AlertMessage(
                alert_id=alert._id,
                phone=phone,
                direction=direction,
                type=msg_type,
                body=data.get('body', ''),
                payload=payload,
                user_id=data.get('user_id'),
                user_name=data.get('user_name'),
                user_role=data.get('user_role', ''),
                is_template=bool(data.get('is_template', False)),
                is_navigation=bool(data.get('is_navigation', False)),
                media_url=media_url,
                mime_type=mime_type,
                wa_message_id=wa_message_id,
                reply_to=reply_to
            )
            created = self.repo.create(message)
            created_data = created.to_json()
            if not created.is_template and not created.is_navigation:
                empresa = EmpresaRepository().find_by_nombre(alert.empresa_nombre)
                publish_realtime_event({
                    'type': 'alert.message.created',
                    'empresaId': str(empresa._id) if empresa else None,
                    'entityId': str(alert._id),
                    'payload': {
                        'alertId': str(alert._id),
                        'message': created_data,
                    },
                })
            return jsonify({'success': True, 'message': created_data}), 201
        except Exception as e:
            return jsonify({'success': False, 'error': 'Error interno', 'message': str(e)}), 500

    def send_group_message(self, alert_id):
        """POST /api/mqtt-alerts/<alert_id>/messages/send - La empresa escribe al grupo de la alerta.

        Envía el texto a todos los contactos de la alerta vía WhatsApp y registra
        un único mensaje saliente que se propaga en vivo por WebSocket.
        """
        try:
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Formato inválido', 'message': 'JSON requerido'}), 400
            data = request.get_json() or {}

            body = (data.get('message') or data.get('body') or '').strip()
            if not body:
                return jsonify({'success': False, 'error': 'El mensaje no puede estar vacío'}), 400

            alert = self.alert_repo.get_alert_by_id(alert_id)
            if not alert:
                return jsonify({'success': False, 'error': 'Alerta no encontrada'}), 404
            if hasattr(alert, 'activo') and not alert.activo:
                return jsonify({'success': False, 'error': 'Alerta inactiva', 'message': 'No se puede escribir en una alerta desactivada'}), 409

            # Destinatarios: todo el "grupo" de la alerta (sus contactos).
            contactos = alert.numeros_telefonicos if getattr(alert, 'numeros_telefonicos', None) else []
            telefonos = []
            for contacto in contactos:
                numero = (contacto or {}).get('numero') if isinstance(contacto, dict) else None
                if numero and numero not in telefonos:
                    telefonos.append(numero)

            if not telefonos:
                return jsonify({'success': False, 'error': 'La alerta no tiene contactos a quienes escribir'}), 400

            # Responder citando un mensaje: resolver el mensaje citado por su _id interno
            # y la cita para el panel. El `context` de WhatsApp solo es válido en la
            # conversación 1:1 del dueño del wamid → se calcula por destinatario.
            reply_to = None
            quoted = None
            reply_to_id = data.get('reply_to_id')
            if reply_to_id:
                candidate = self.repo.find_by_id(reply_to_id)
                if candidate and str(candidate.alert_id) == str(alert._id):
                    quoted = candidate
                    reply_to = self._build_reply_preview(quoted)

            # Titular del mensaje que llega por WhatsApp = nombre de la empresa (en
            # negrita como primera línea; el texto libre de WhatsApp no tiene header).
            titular = (data.get('user_name') or alert.empresa_nombre or '').strip()
            whatsapp_body = f"*{titular}*\n{body}" if titular else body

            enviados, fallidos, wa_recipients = [], [], []
            for numero in telefonos:
                context_message_id = self._context_for_recipient(quoted, numero) if quoted else None
                result = whatsapp_client.send_text_message(numero, whatsapp_body, context_message_id=context_message_id)
                if result.get('success'):
                    enviados.append({'numero': numero})
                    wamid = self._extract_wamid(result)
                    if wamid:
                        wa_recipients.append({'phone': numero, 'wa_message_id': wamid})
                else:
                    fallidos.append({'numero': numero, 'error': result.get('error')})

            # Si ninguno se pudo enviar, no registrar el mensaje: evita historial engañoso.
            if not enviados:
                return jsonify({
                    'success': False,
                    'error': 'No se pudo enviar el mensaje a ningún contacto',
                    'detalle': fallidos,
                }), 502

            empresa = EmpresaRepository().find_by_nombre(alert.empresa_nombre)
            message = AlertMessage(
                alert_id=alert._id,
                phone=data.get('phone') or '',
                direction=AlertMessage.DIRECTION_OUT,
                type='text',
                body=body,
                user_name=data.get('user_name') or (empresa.nombre if empresa else alert.empresa_nombre),
                user_role=data.get('user_role') or 'empresa',
                wa_recipients=wa_recipients,
                reply_to=reply_to,
            )
            created = self.repo.create(message)
            created_data = created.to_json()
            publish_realtime_event({
                'type': 'alert.message.created',
                'empresaId': str(empresa._id) if empresa else None,
                'entityId': str(alert._id),
                'payload': {
                    'alertId': str(alert._id),
                    'message': created_data,
                },
            })
            return jsonify({
                'success': True,
                'message': created_data,
                'enviados': enviados,
                'fallidos': fallidos,
            }), 201
        except Exception as e:
            return jsonify({'success': False, 'error': 'Error interno', 'message': str(e)}), 500

    def add_message_recipients(self, alert_id):
        """POST /api/mqtt-alerts/<alert_id>/messages/recipients

        Adjunta los wamids de las copias reenviadas (uno por miembro) al mensaje de
        origen, para que la respuesta se vea como reply nativo para todo el grupo.
        """
        try:
            data = request.get_json(silent=True) or {}
            origin = data.get('origin_wa_message_id')
            recipients = data.get('recipients') or []
            if not origin or not isinstance(recipients, list):
                return jsonify({'success': False, 'error': 'origin_wa_message_id y recipients requeridos'}), 400
            found = self.repo.add_recipients(alert_id, origin, recipients)
            if not found:
                return jsonify({'success': False, 'error': 'Mensaje de origen no encontrado'}), 404
            return jsonify({'success': True}), 200
        except Exception as e:
            return jsonify({'success': False, 'error': 'Error interno', 'message': str(e)}), 500

    def get_context_map(self, alert_id):
        """GET /api/mqtt-alerts/<alert_id>/messages/context-map?wamid=<quoted>

        Devuelve {digits(phone): wamid} del mensaje citado (identificado por el wamid de
        cualquiera de sus copias), para que MQTTArisma reenvíe la respuesta con el
        `context` correcto en la conversación 1:1 de cada miembro.
        """
        try:
            wamid = request.args.get('wamid')
            if not wamid:
                return jsonify({'success': False, 'error': 'wamid requerido'}), 400
            msg = self.repo.find_by_wa_id(alert_id, wamid)
            mapa = {}
            if msg:
                if msg.direction == AlertMessage.DIRECTION_IN and msg.wa_message_id:
                    mapa[self._digits(msg.phone)] = msg.wa_message_id
                for rec in (msg.wa_recipients or []):
                    if rec.get('wa_message_id'):
                        mapa[self._digits(rec.get('phone'))] = rec.get('wa_message_id')
            return jsonify({'success': True, 'map': mapa}), 200
        except Exception as e:
            return jsonify({'success': False, 'error': 'Error interno', 'message': str(e)}), 500

    def serve_media(self, file_id):
        """GET /api/mqtt-alerts/media/<file_id> - Sirve un archivo de GridFS.

        Soporta `Range` (respuesta 206) para que audio/video permitan scrub.
        """
        try:
            grid_out = self.media_repo.get(file_id)
            if grid_out is None:
                return jsonify({'success': False, 'error': 'Archivo no encontrado'}), 404

            content_type = getattr(grid_out, 'content_type', None) or 'application/octet-stream'
            file_length = grid_out.length
            range_header = request.headers.get('Range')

            if range_header and range_header.startswith('bytes='):
                spec = range_header.split('=', 1)[1].split(',')[0].strip()
                start_str, _, end_str = spec.partition('-')
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_length - 1
                start = max(0, start)
                end = min(end, file_length - 1)
                if start > end:
                    start, end = 0, file_length - 1
                grid_out.seek(start)
                chunk = grid_out.read(end - start + 1)
                resp = Response(chunk, 206, mimetype=content_type)
                resp.headers['Content-Range'] = f'bytes {start}-{end}/{file_length}'
                resp.headers['Accept-Ranges'] = 'bytes'
                resp.headers['Content-Length'] = str(len(chunk))
                return resp

            resp = Response(grid_out.read(), 200, mimetype=content_type)
            resp.headers['Accept-Ranges'] = 'bytes'
            resp.headers['Content-Length'] = str(file_length)
            resp.headers['Cache-Control'] = 'private, max-age=86400'
            return resp
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
