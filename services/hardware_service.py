from bson import ObjectId
from datetime import datetime, timedelta, timezone
from models.hardware import Hardware
from repositories.hardware_repository import HardwareRepository
from repositories.empresa_repository import EmpresaRepository
from repositories.mqtt_alert_repository import MqttAlertRepository
from services.hardware_type_service import HardwareTypeService
from utils.geocoding import procesar_direccion_para_hardware
from core.config import Config

class HardwareService:
    def __init__(self):
        self.hardware_repo = HardwareRepository()
        self.empresa_repo = EmpresaRepository()
        self.type_service = HardwareTypeService()
        self.mqtt_alert_repo = MqttAlertRepository()


    def _get_empresa(self, empresa_nombre):
        """Obtiene la empresa a partir de su nombre."""
        return self.empresa_repo.find_by_nombre(empresa_nombre)
    
    def _procesar_direccion(self, direccion):
        """Procesa una dirección y devuelve URLs, coordenadas y posible error."""
        if not direccion:
            return None, None, None, "La dirección es obligatoria"
        return procesar_direccion_para_hardware(direccion)
    
    def _get_topics_otros_hardware_from_alerts(self, hardware_topic):
        """Obtiene los topics de otros hardware que están vinculados en alertas con este hardware"""
        try:
            # Buscar alertas que contengan el topic del hardware desactivado
            # Buscar en el campo 'topic' (hardware principal) o 'topics_otros_hardware' (hardware secundario)
            query = {
                '$or': [
                    {'topic': hardware_topic},  # Hardware principal de la alerta
                    {'topics_otros_hardware': hardware_topic}  # Hardware secundario
                ]
            }
            
            alerts_data = self.mqtt_alert_repo.collection.find(query)
            topics_otros_hardware = set()  # Usar set para evitar duplicados
            
            for alert_data in alerts_data:
                # Si el hardware desactivado es el principal, agregar todos los otros
                if alert_data.get('topic') == hardware_topic:
                    otros_topics = alert_data.get('topics_otros_hardware', [])
                    topics_otros_hardware.update(otros_topics)
                
                # Si el hardware desactivado está en otros_hardware, agregar el principal y el resto
                elif hardware_topic in alert_data.get('topics_otros_hardware', []):
                    # Agregar el topic principal
                    main_topic = alert_data.get('topic')
                    if main_topic:
                        topics_otros_hardware.add(main_topic)
                    
                    # Agregar los otros topics (excluyendo el actual)
                    otros_topics = alert_data.get('topics_otros_hardware', [])
                    for topic in otros_topics:
                        if topic != hardware_topic:
                            topics_otros_hardware.add(topic)
            
            return list(topics_otros_hardware)
        except Exception as e:
            # print(f"Error obteniendo topics de otros hardware: {e}")
            return []

    def create_hardware(self, data):
        try:
            nombre = data.pop('nombre', None)
            tipo = data.pop('tipo', None)
            sede = data.pop('sede', None)
            direccion = data.pop('direccion', None)  # Nueva dirección
            nombre_empresa = data.pop('empresa_nombre', None)
            if not nombre_empresa:
                return {'success': False, 'errors': ['El nombre de la empresa es obligatorio']}
            empresa = self._get_empresa(nombre_empresa)
            if not empresa:
                return {'success': False, 'errors': ['Empresa no encontrada']}
            if not sede:
                return {'success': False, 'errors': ['La sede es obligatoria']}
            if sede not in (empresa.sedes or []):
                return {'success': False, 'errors': ['La sede no pertenece a la empresa']}
            if not nombre:
                return {'success': False, 'errors': ['El nombre del hardware es obligatorio']}
            if not direccion:
                return {'success': False, 'errors': ['La dirección es obligatoria']}
            if self.hardware_repo.find_by_nombre(nombre):
                return {'success': False, 'errors': ['Ya existe un hardware con ese nombre']}
            if tipo not in self.type_service.get_type_names():
                return {'success': False, 'errors': ['Tipo de hardware no soportado']}
            # Si los datos vienen con un campo 'datos', extraerlo; si no, usar data directamente
            datos_finales = data.get('datos', data) if 'datos' in data else data
            
            # Procesar dirección y geocodificar
            direccion_url_google, direccion_url_openstreetmap, coordenadas, direccion_error = self._procesar_direccion(direccion)
            if direccion_error:
                return {'success': False, 'errors': [direccion_error]}
            
            # Crear instancia de hardware y generar topic automáticamente
            hardware = Hardware(nombre=nombre, tipo=tipo, empresa_id=empresa._id, sede=sede, datos=datos_finales)
            hardware.direccion = direccion
            hardware.direccion_url = direccion_url_google
            hardware.direccion_open_maps = direccion_url_openstreetmap
            hardware.coordenadas = coordenadas  # Nuevo campo para coordenadas
            hardware.topic = hardware.generate_topic(nombre_empresa, sede, tipo, nombre)
            excluded_types = [
                item.strip().upper()
                for item in (Config.HARDWARE_STATUS_DEFAULT_EXCLUDED_TYPES or '').split(',')
                if item.strip()
            ]
            if tipo.upper() not in excluded_types:
                hardware.physical_status = {'estado': 'Inactivo'}
            
            created = self.hardware_repo.create(hardware)
            result = created.to_json()
            result['empresa_nombre'] = nombre_empresa
            return {'success': True, 'data': result}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def get_all_hardware(self, filters=None):
        try:
            if filters:
                hardware_list = self.hardware_repo.find_with_filters(filters)
            else:
                hardware_list = self.hardware_repo.find_all()
            
            resultados = []
            for h in hardware_list:
                empresa = self.empresa_repo.find_by_id(h.empresa_id) if h.empresa_id else None
                j = h.to_json()
                j['empresa_nombre'] = empresa.nombre if empresa else None
                resultados.append(j)
            return {'success': True, 'data': resultados, 'count': len(resultados)}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def get_hardware(self, hardware_id):
        try:
            hardware = self.hardware_repo.find_by_id(hardware_id)
            if not hardware:
                return {'success': False, 'errors': ['Hardware no encontrado']}
            empresa = self.empresa_repo.find_by_id(hardware.empresa_id) if hardware.empresa_id else None
            result = hardware.to_json()
            result['empresa_nombre'] = empresa.nombre if empresa else None
            return {'success': True, 'data': result}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def get_hardware_including_inactive(self, hardware_id):
        """Obtiene hardware por ID incluyendo inactivos (para admins)"""
        try:
            hardware = self.hardware_repo.find_by_id_including_inactive(hardware_id)
            if not hardware:
                return {'success': False, 'errors': ['Hardware no encontrado']}
            empresa = self.empresa_repo.find_by_id(hardware.empresa_id) if hardware.empresa_id else None
            result = hardware.to_json()
            result['empresa_nombre'] = empresa.nombre if empresa else None
            return {'success': True, 'data': result}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def get_hardware_by_empresa(self, empresa_id):
        try:
            hardware_list = self.hardware_repo.find_by_empresa(empresa_id)
            empresa = self.empresa_repo.find_by_id(empresa_id)
            nombre = empresa.nombre if empresa else None
            resultados = []
            for h in hardware_list:
                j = h.to_json()
                j['empresa_nombre'] = nombre
                resultados.append(j)
            return {'success': True, 'data': resultados, 'count': len(resultados)}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def get_all_hardware_including_inactive(self, filters=None):
        """Obtiene todos los hardware incluyendo los inactivos"""
        try:
            if filters:
                hardware_list = self.hardware_repo.find_with_filters_including_inactive(filters)
            else:
                hardware_list = self.hardware_repo.find_all_including_inactive()
            
            resultados = []
            for h in hardware_list:
                empresa = self.empresa_repo.find_by_id(h.empresa_id) if h.empresa_id else None
                j = h.to_json()
                j['empresa_nombre'] = empresa.nombre if empresa else None
                resultados.append(j)
            return {'success': True, 'data': resultados, 'count': len(resultados)}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def get_hardware_by_empresa_including_inactive(self, empresa_id):
        """Obtiene todos los hardware de una empresa incluyendo los inactivos"""
        try:
            hardware_list = self.hardware_repo.find_by_empresa_including_inactive(empresa_id)
            empresa = self.empresa_repo.find_by_id(empresa_id)
            nombre = empresa.nombre if empresa else None
            resultados = []
            for h in hardware_list:
                j = h.to_json()
                j['empresa_nombre'] = nombre
                resultados.append(j)
            return {'success': True, 'data': resultados, 'count': len(resultados)}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def update_hardware(self, hardware_id, data):
        try:
            existing = self.hardware_repo.find_by_id_including_inactive(hardware_id)
            if not existing:
                return {'success': False, 'errors': ['Hardware no encontrado']}
            nombre = data.pop('nombre', existing.nombre)
            tipo = data.pop('tipo', existing.tipo)
            sede = data.pop('sede', existing.sede)
            direccion = data.pop('direccion', existing.direccion)  # Nueva dirección
            nombre_empresa = data.pop('empresa_nombre', None)
            empresa = None
            empresa_id = existing.empresa_id
            # Validar nombres duplicados solo si el nombre cambió
            if nombre != existing.nombre:
                existing_hardware = self.hardware_repo.find_by_nombre_excluding_id(nombre, hardware_id)
                if existing_hardware:
                    return {'success': False, 'errors': ['Ya existe un hardware con ese nombre']}
            if nombre_empresa:
                empresa = self._get_empresa(nombre_empresa)
                if not empresa:
                    return {'success': False, 'errors': ['Empresa no encontrada']}
                empresa_id = empresa._id
            else:
                empresa = self.empresa_repo.find_by_id(existing.empresa_id) if existing.empresa_id else None
            if not sede:
                return {'success': False, 'errors': ['La sede es obligatoria']}
            if not direccion:
                return {'success': False, 'errors': ['La dirección es obligatoria']}
            if empresa and sede not in (empresa.sedes or []):
                return {'success': False, 'errors': ['La sede no pertenece a la empresa']}
            if tipo not in self.type_service.get_type_names():
                return {'success': False, 'errors': ['Tipo de hardware no soportado']}
            # Si los datos vienen con un campo 'datos', extraerlo; si no, usar data directamente
            datos_finales = data.get('datos', data) if 'datos' in data else data
            
            # Procesar dirección solo si cambió
            direccion_url_google = existing.direccion_url
            direccion_url_openstreetmap = getattr(existing, 'direccion_open_maps', None)
            coordenadas = getattr(existing, 'coordenadas', None)
            
            if direccion != getattr(existing, 'direccion', None):
                # print(f'🗺️ Dirección cambió, geocodificando nueva dirección: {direccion}')
                direccion_url_google, direccion_url_openstreetmap, coordenadas, direccion_error = self._procesar_direccion(direccion)
                if direccion_error:
                    return {'success': False, 'errors': [direccion_error]}
            else:
                # print(f'🔄 Dirección sin cambios, manteniendo URLs existentes')
                pass
            
            # Crear instancia actualizada y regenerar topic automáticamente
            updated = Hardware(nombre=nombre, tipo=tipo, empresa_id=empresa_id, sede=sede, datos=datos_finales, _id=existing._id, activa=existing.activa)
            updated.direccion = direccion
            updated.direccion_url = direccion_url_google
            updated.direccion_open_maps = direccion_url_openstreetmap
            updated.coordenadas = coordenadas
            updated.fecha_creacion = existing.fecha_creacion
            updated.physical_status = existing.physical_status or {}
            
            # Regenerar topic con los nuevos datos
            empresa_nombre_final = nombre_empresa if nombre_empresa else (empresa.nombre if empresa else None)
            if empresa_nombre_final:
                updated.topic = updated.generate_topic(empresa_nombre_final, sede, tipo, nombre)
            
            result = self.hardware_repo.update(hardware_id, updated)
            if result:
                res = result.to_json()
                empresa = self.empresa_repo.find_by_id(result.empresa_id) if result.empresa_id else None
                res['empresa_nombre'] = empresa.nombre if empresa else None
                return {'success': True, 'data': res}
            else:
                return {'success': False, 'errors': ['Error actualizando hardware']}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def delete_hardware(self, hardware_id):
        try:
            deleted = self.hardware_repo.soft_delete(hardware_id)
            if deleted:
                return {'success': True, 'message': 'Hardware eliminado correctamente'}
            return {'success': False, 'errors': ['Error eliminando hardware']}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def toggle_hardware_status(self, hardware_id, activa):
        """Activar o desactivar hardware"""
        try:
            existing = self.hardware_repo.find_by_id_including_inactive(hardware_id)
            if not existing:
                return {'success': False, 'errors': ['Hardware no encontrado']}
            
            # Si se está desactivando el hardware (activa=False), buscar topics de otros hardware vinculados
            topics_otros_hardware = []
            if not activa and existing.topic:  # Solo si se desactiva y tiene topic
                topics_otros_hardware = self._get_topics_otros_hardware_from_alerts(existing.topic)
            
            # Actualizar solo el campo activa
            existing.activa = activa
            existing.update_timestamp()
            
            updated = self.hardware_repo.update(hardware_id, existing)
            if updated:
                status_text = "activado" if activa else "desactivado"
                result = updated.to_json()
                empresa = self.empresa_repo.find_by_id(updated.empresa_id) if updated.empresa_id else None
                result['empresa_nombre'] = empresa.nombre if empresa else None
                
                response = {
                    'success': True, 
                    'data': result,
                    'message': f'Hardware {status_text} exitosamente'
                }
                
                # Si se desactivó y hay topics de otros hardware, incluirlos en la respuesta
                if not activa and topics_otros_hardware:
                    response['topics_otros_hardware'] = topics_otros_hardware
                    response['message'] += f'. Se encontraron {len(topics_otros_hardware)} hardware(s) vinculado(s) en alertas.'
                
                return response
            return {'success': False, 'errors': ['Error al actualizar el estado del hardware']}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}
    
    def get_hardware_direccion_url(self, hardware_id):
        """Obtiene solo la URL de dirección de un hardware específico"""
        try:
            hardware = self.hardware_repo.find_by_id_including_inactive(hardware_id)
            if not hardware:
                return {'success': False, 'errors': ['Hardware no encontrado']}
            
            # Retornar solo la información de dirección
            direccion_data = {
                'id': str(hardware._id),
                'nombre': hardware.nombre,
                'direccion': hardware.direccion,
                'direccion_url': hardware.direccion_url,
                'direccion_open_maps': getattr(hardware, 'direccion_open_maps', None)
            }
            
            return {'success': True, 'data': direccion_data}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def update_physical_status(self, empresa_nombre, hardware_nombre, physical_status):
        """Actualiza solo el campo physical_status usando empresa + hardware"""
        try:
            if not (empresa_nombre and hardware_nombre):
                return {
                    'success': False,
                    'errors': ['Debe enviar empresa_nombre y hardware_nombre']
                }
            if physical_status is None or not isinstance(physical_status, dict):
                return {'success': False, 'errors': ['physical_status debe ser un objeto JSON']}

            physical_status['updated_at'] = datetime.utcnow().isoformat()
            update_result = self.hardware_repo.update_physical_status_by_empresa_hardware(
                empresa_nombre,
                hardware_nombre,
                physical_status
            )
            if not update_result:
                return {'success': False, 'errors': ['Hardware no encontrado']}
            updated, previous_status = update_result

            result = updated.to_json()
            empresa = self.empresa_repo.find_by_id(updated.empresa_id) if updated.empresa_id else None
            result['empresa_nombre'] = empresa.nombre if empresa else None
            previous_state = str((previous_status or {}).get('estado') or '').strip().lower()
            current_state = str(physical_status.get('estado') or '').strip().lower()
            return {
                'success': True,
                'data': result,
                'status_changed': previous_state != current_state,
                'previous_state': (previous_status or {}).get('estado'),
            }
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}

    def check_physical_status_stale(self, empresa_id=None):
        """Marca como inactivo el hardware con status vencido"""
        try:
            excluded_types = [
                item.strip().upper()
                for item in (Config.HARDWARE_STATUS_DEFAULT_EXCLUDED_TYPES or '').split(',')
                if item.strip()
            ]
            stale_seconds = Config.HARDWARE_STATUS_STALE_SECONDS
            now = datetime.utcnow()

            if empresa_id:
                hardware_list = self.hardware_repo.find_by_empresa(empresa_id)
            else:
                hardware_list = self.hardware_repo.find_all()

            updated_hardware = []
            for hardware in hardware_list:
                if not hardware.activa:
                    continue
                tipo = (hardware.tipo or '').upper()
                if tipo in excluded_types:
                    continue

                physical_status = hardware.physical_status or {}
                estado_actual = physical_status.get('estado')
                updated_at = physical_status.get('updated_at')
                last_update = None
                if isinstance(updated_at, str):
                    try:
                        last_update = datetime.fromisoformat(updated_at)
                        if last_update.tzinfo is not None:
                            last_update = last_update.astimezone(timezone.utc).replace(tzinfo=None)
                    except ValueError:
                        last_update = None

                is_stale = not last_update or (now - last_update) > timedelta(seconds=stale_seconds)
                normalized_state = estado_actual.strip().lower() if isinstance(estado_actual, str) else ''
                should_be_inactive = normalized_state == 'desactivado' or is_stale
                if not should_be_inactive or normalized_state == 'inactivo':
                    continue
                physical_status['estado'] = 'Inactivo'
                updated = self.hardware_repo.update_physical_status_by_id(hardware._id, physical_status)
                if updated:
                    empresa = self.empresa_repo.find_by_id(updated.empresa_id) if updated.empresa_id else None
                    hardware_data = updated.to_json()
                    hardware_data['empresa_nombre'] = empresa.nombre if empresa else None
                    updated_hardware.append(hardware_data)

            return {'success': True, 'data': updated_hardware, 'count': len(updated_hardware)}
        except Exception as exc:
            return {'success': False, 'errors': [str(exc)]}
