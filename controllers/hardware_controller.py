from flask import request, jsonify
from services.hardware_service import HardwareService
from decorators.internal_token_decorator import require_internal_token
from utils.permissions import require_super_admin_token

class HardwareController:
    def __init__(self):
        self.service = HardwareService()

    @require_super_admin_token
    def create_hardware(self):
        try:
            data = request.get_json() or {}
            result = self.service.create_hardware(data)
            status = 201 if result.get('success') else 400
            return jsonify(result), status
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500

    @require_super_admin_token
    def get_hardware_list(self):
        """Obtener todos los hardware activos (solo super admin)"""
        try:
            # Get query parameters for filtering
            filters = {}
            
            if request.args.get('tipo'):
                filters['tipo'] = request.args.get('tipo')
            
            if request.args.get('empresa_id'):
                filters['empresa_id'] = request.args.get('empresa_id')
            
            if request.args.get('sede'):
                filters['sede'] = request.args.get('sede')
            
            if request.args.get('search'):
                filters['search'] = request.args.get('search')
            
            if request.args.get('status'):
                filters['status'] = request.args.get('status')
            
            if request.args.get('min_stock'):
                try:
                    filters['min_stock'] = int(request.args.get('min_stock'))
                except ValueError:
                    pass
            
            # Pass filters to service if any exist
            filter_params = filters if filters else None
            result = self.service.get_all_hardware(filter_params)
            status = 200 if result.get('success') else 500
            return jsonify(result), status
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500

    def get_hardware(self, hardware_id):
        try:
            # Use get_hardware_including_inactive to fetch by ID including inactive
            result = self.service.get_hardware_including_inactive(hardware_id)
            # print(f"el result de get_hardware trae esto: {result}")
            status = 200 if result.get('success') else 404
            return jsonify(result), status
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500

    @require_super_admin_token
    def update_hardware(self, hardware_id):
        try:
            data = request.get_json() or {}
            # print(f"json entrante: {data} ")
            result = self.service.update_hardware(hardware_id, data)
            # print(f"result: {result}")
            status = 200 if result.get('success') else 400
            return jsonify(result), status
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500

    @require_super_admin_token
    def delete_hardware(self, hardware_id):
        try:
            result = self.service.delete_hardware(hardware_id)
            status = 200 if result.get('success') else 404
            return jsonify(result), status
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500

    def get_hardware_by_empresa(self, empresa_id):
        try:
            result = self.service.get_hardware_by_empresa(empresa_id)
            status = 200 if result.get('success') else 404
            return jsonify(result), status
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500

    @require_super_admin_token
    def toggle_hardware_status(self, hardware_id):
        """Activar o desactivar hardware"""
        try:
            data = request.get_json() or {}
            activa = data.get('activa', True)
            result = self.service.toggle_hardware_status(hardware_id, activa)
            status = 200 if result.get('success') else 404
            return jsonify(result), status
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500

    @require_super_admin_token
    def get_all_hardware_including_inactive(self):
        """Obtener todos los hardware incluyendo inactivos (solo super admin)"""
        try:
            # Get query parameters for filtering
            filters = {}
            
            if request.args.get('tipo'):
                filters['tipo'] = request.args.get('tipo')
            
            if request.args.get('empresa_id'):
                filters['empresa_id'] = request.args.get('empresa_id')
            
            if request.args.get('sede'):
                filters['sede'] = request.args.get('sede')
            
            if request.args.get('search'):
                filters['search'] = request.args.get('search')
            
            if request.args.get('status'):
                filters['status'] = request.args.get('status')
            
            if request.args.get('activa') is not None:
                filters['activa'] = request.args.get('activa').lower() == 'true'
            
            if request.args.get('min_stock'):
                try:
                    filters['min_stock'] = int(request.args.get('min_stock'))
                except ValueError:
                    pass
            
            # Pass filters to service if any exist
            filter_params = filters if filters else None
            result = self.service.get_all_hardware_including_inactive(filter_params)
            status = 200 if result.get('success') else 500
            return jsonify(result), status
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500

    def get_hardware_by_empresa_including_inactive(self, empresa_id):
        """Obtener hardware de una empresa incluyendo inactivos"""
        try:
            result = self.service.get_hardware_by_empresa_including_inactive(empresa_id)
            status = 200 if result.get('success') else 404
            return jsonify(result), status
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500
    
    def get_hardware_direccion_url(self, hardware_id):
        """Obtener solo la URL de dirección de un hardware específico"""
        try:
            result = self.service.get_hardware_direccion_url(hardware_id)
            status = 200 if result.get('success') else 404
            return jsonify(result), status
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500

    @require_internal_token
    def update_physical_status_by_topic(self):
        """Actualizar physical_status por empresa y hardware (token interno)"""
        try:
            data = request.get_json(silent=True) or {}
            empresa_nombre = data.get('empresa_nombre')
            hardware_nombre = data.get('hardware_nombre')
            physical_status = data.get('physical_status')
            result = self.service.update_physical_status(empresa_nombre, hardware_nombre, physical_status)
            if result.get('success'):
                hardware = result.get('data') or {}
                if result.get('status_changed'):
                    from utils.realtime_publisher import publish_realtime_event
                    publish_realtime_event({
                        'type': 'hardware.status.changed',
                        'empresaId': hardware.get('empresa_id'),
                        'entityId': hardware.get('_id'),
                        'payload': {
                            'hardware': hardware,
                            'previousStatus': result.get('previous_state'),
                            'reason': 'status_received',
                        },
                    })
                return jsonify(result), 200
            if 'Hardware no encontrado' in result.get('errors', []):
                return jsonify(result), 404
            return jsonify(result), 400
        except Exception as exc:
            return jsonify({'success': False, 'errors': [str(exc)]}), 500

