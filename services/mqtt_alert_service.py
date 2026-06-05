from repositories.mqtt_alert_repository import MqttAlertRepository
from repositories.usuario_repository import UsuarioRepository
from models.mqtt_alert import MqttAlert
from datetime import datetime
import json

class MqttAlertService:
    """Servicio para manejar alertas MQTT"""
    
    def __init__(self):
        self.alert_repo = MqttAlertRepository()
        self.usuario_repo = UsuarioRepository()
    
    def process_mqtt_message(self, mqtt_data):
        """Procesa un mensaje MQTT y crea una alerta"""
        try:
            if not isinstance(mqtt_data, dict):
                return {'success': False, 'error': 'Formato de datos inválido'}

            empresa = mqtt_data.get('empresa') or ''
            sede = mqtt_data.get('sede') or ''
            tipo_hardware = mqtt_data.get('tipo_hardware') or ''
            nombre_hardware = mqtt_data.get('nombre_hardware') or ''
            data = mqtt_data.get('data') or {}

            tipo_alerta = data.get('tipo_alarma') or ''

            datos_hardware = {
                'nombre': nombre_hardware,
                'sede': sede,
                'tipo': tipo_hardware,
            }

            result = self._create_alert_from_mqtt(
                empresa_nombre=empresa,
                tipo_alerta=tipo_alerta,
                datos_hardware=datos_hardware,
                mensaje_original=mqtt_data
            )
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Error procesando mensaje MQTT'
            }
    
    def _create_alert_from_mqtt(self, empresa_nombre, tipo_alerta, datos_hardware, mensaje_original):
        """Crea una alerta desde datos MQTT"""
        try:
            # Extraer información del hardware
            sede = datos_hardware.get('sede', 'sede_desconocida')
            hardware_nombre = datos_hardware.get('nombre') or datos_hardware.get('hardware_id') or datos_hardware.get('id')
            
            # FILTRO INICIAL: Verificar hardware como primera validación
            if not hardware_nombre:
                return {
                    'success': False,
                    'error': 'Nombre del hardware es requerido',
                    'empresa': empresa_nombre,
                    'sede': sede
                }
            
            # Verificación completa: hardware, empresa, sede y usuarios
            verification_info = self.alert_repo.get_full_verification_info(hardware_nombre)
            
            # Determinar estados según verificación
            if not verification_info['hardware_exists']:
                # Hardware no existe: autorizado=false, estado_activo=false
                autorizado = False
                estado_activo = False
                usuarios = []
                
                # Aún extraer empresa y sede del mensaje para guardar
                empresa_nombre_final = empresa_nombre
                sede_final = sede
                
            else:
                # Hardware existe: verificar empresa y sede
                hardware_data = verification_info['hardware_data']
                empresa_data = verification_info.get('empresa_data', {})
                
                # Usar datos del hardware si están disponibles
                empresa_nombre_final = empresa_data.get('nombre', empresa_nombre)
                sede_final = hardware_data.get('sede', sede)
                
                # Estados según verificación
                if verification_info['empresa_exists'] and verification_info['sede_exists']:
                    # Todo correcto: autorizado=false (pendiente), estado_activo=true
                    autorizado = False
                    estado_activo = True
                    usuarios = verification_info['usuarios']
                else:
                    # Hardware existe pero empresa/sede no: autorizado=false, estado_activo=false
                    autorizado = False
                    estado_activo = False
                    usuarios = []
            
            # Obtener usuarios para notificación
            
            # Preparar lista de usuarios notificados
            usuarios_notificados = []
            for usuario in usuarios:
                usuario_info = {
                    'nombre': usuario.get('nombre'),
                    'telefono': usuario.get('telefono'),
                    'email': usuario.get('email'),
                    'rol': usuario.get('rol'),
                    'especialidades': usuario.get('especialidades', [])
                }
                usuarios_notificados.append(usuario_info)
            
            # Preparar datos adicionales (ruta, origen, etc.)
            data_adicional = {
                'ruta_origen': 'mqtt://empresas',  # ruta del topic MQTT
                'protocolo': 'MQTT',
                'broker': '161.35.239.177:17090',
                'topic_completo': f'empresas/{empresa_nombre_final}',
                'timestamp_procesamiento': datetime.utcnow().isoformat(),
                'cliente_origen': 'MqttConnection-Service',
                'verificacion': {
                    'hardware_exists': verification_info['hardware_exists'],
                    'empresa_exists': verification_info.get('empresa_exists', False),
                    'sede_exists': verification_info.get('sede_exists', False)
                },
                'metadatos': {
                    'tamano_mensaje': len(str(mensaje_original)),
                    'tipo_procesamiento': 'automatico',
                    'nivel_prioridad': self._determine_priority(tipo_alerta, datos_hardware)
                }
            }
            
            # Obtener hardware_id si está disponible en auth_info
            hardware_id = None
            if isinstance(mensaje_original, dict) and 'auth_info' in mensaje_original:
                hardware_id = mensaje_original['auth_info'].get('hardware_id')
            
            # Agregar información adicional a los datos
            data_adicional['datos_hardware'] = datos_hardware
            data_adicional['mensaje_original'] = mensaje_original
            data_adicional['usuarios_notificados'] = usuarios_notificados
            data_adicional['autorizado'] = autorizado
            data_adicional['estado_activo'] = estado_activo
            
            # Determinar prioridad de la alerta
            prioridad_alerta = self._determine_priority(tipo_alerta, datos_hardware)
            
            # Obtener imagen de la alerta desde tipo_alarma_info si existe
            image_alert = None
            # TODO: Implementar búsqueda de tipo_alarma_info si es necesario
            
            # Preparar información de ubicación desde el hardware asociado (si existe)
            ubicacion_info = {
                'direccion': '',
                'url_maps': '',
                'url_open_maps': ''
            }
            if verification_info.get('hardware_exists') and hardware_data:
                ubicacion_info = {
                    'direccion': hardware_data.get('direccion') or '',
                    'url_maps': hardware_data.get('direccion_url') or '',
                    'url_open_maps': hardware_data.get('direccion_open_maps') or ''
                }
            
            # Preparar números telefónicos (excluir alert managers)
            numeros_telefonicos = []
            for usuario in usuarios:
                telefono = usuario.get('telefono')
                if not telefono:
                    continue
                rol_det = usuario.get('rol_detalle') or {}
                if isinstance(rol_det, dict) and rol_det.get('is_alert_manager'):
                    continue
                numeros_telefonicos.append({
                    'numero': telefono,
                    'nombre': usuario.get('nombre', ''),
                    'usuario_id': str(usuario.get('_id')),
                    'rol': rol_det,
                    'disponible': False,
                    'embarcado': False
                })
            
            # Obtener topics de otros hardware (excluir botoneras) para fanout MQTT
            topics_otros_hardware = []
            try:
                empresa_data_local = verification_info.get('empresa_data') or {}
                empresa_id_local = empresa_data_local.get('_id')
                if empresa_id_local and sede_final:
                    from repositories.hardware_repository import HardwareRepository
                    hw_repo = HardwareRepository()
                    todos_hw = hw_repo.find_with_filters({
                        'empresa_id': empresa_id_local,
                        'sede': sede_final,
                    })
                    topics_otros_hardware = [
                        hw.topic for hw in todos_hw
                        if hw.topic and hw.tipo.upper() != 'BOTONERA'
                    ]
            except Exception:
                topics_otros_hardware = []
            
            # Crear la alerta usando el método de fábrica actualizado
            alert = MqttAlert.create_from_hardware(
                empresa_nombre=empresa_nombre_final,
                sede=sede_final,
                hardware_nombre=hardware_nombre,
                hardware_id=hardware_id,
                tipo_alerta=tipo_alerta,
                descripcion=f'Alerta MQTT generada por {hardware_nombre}',
                prioridad=prioridad_alerta,
                image_alert=image_alert,
                data=data_adicional,
                numeros_telefonicos=numeros_telefonicos,
                topic='',  # Vacío para alertas MQTT
                topics_otros_hardware=topics_otros_hardware,
                ubicacion=ubicacion_info
            )
            # Validar datos
            errors = alert.validate()
            if errors:
                return {
                    'success': False,
                    'error': 'Datos inválidos',
                    'validation_errors': errors
                }
            
            # Guardar en base de datos
            created_alert = self.alert_repo.create_alert(alert)
            
            return {
                'success': True,
                'alert_id': str(created_alert._id),
                'empresa': empresa_nombre_final,
                'sede': sede_final,
                'tipo_alerta': tipo_alerta,
                'hardware_nombre': hardware_nombre,
                'hardware_exists': verification_info['hardware_exists'],
                'empresa_exists': verification_info.get('empresa_exists', False),
                'sede_exists': verification_info.get('sede_exists', False),
                'autorizado': autorizado,
                'estado_activo': estado_activo,
                'usuarios_notificados': usuarios_notificados,
                'message': 'Alerta creada exitosamente'
            }
            
        except Exception as e:
            # print(f"Error creando alerta desde MQTT: {e}")
            return {
                'success': False,
                'error': str(e),
                'empresa': empresa_nombre,
                'sede': sede if 'sede' in locals() else 'desconocida'
            }
    
    def get_all_alerts(self, page=1, limit=50):
        """Obtiene todas las alertas"""
        try:
            alerts, total = self.alert_repo.get_all_alerts(page, limit)
            return {
                'success': True,
                'alerts': [alert.to_json() for alert in alerts],
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit
            }
        except Exception as e:
            # print(f"Error obteniendo alertas: {e}")
            return {
                'success': False,
                'error': str(e),
                'alerts': [],
                'total': 0
            }
    
    def get_alert_by_id(self, alert_id):
        """Obtiene una alerta por ID"""
        try:
            # print(f"🔍 Servicio: Buscando alerta con ID: {alert_id}")
            alert = self.alert_repo.get_alert_by_id(alert_id)
            # print(f"📊 Alerta obtenida del repo: {alert}")
            if alert:
                # print(f"✅ Alerta encontrada, convirtiendo a JSON...")
                json_data = alert.to_json()
                # print(f"📝 JSON generado: {json_data}")
                
                # COMENTADO: La ubicación ya viene incluida en el modelo actualizado
                # ubicacion_info = self._get_botonera_ubicacion(alert.empresa_nombre, alert.sede)
                # json_data['ubicacion'] = ubicacion_info
                
                return {
                    'success': True,
                    'alert': json_data
                }
            else:
                # print(f"❌ Alerta NO encontrada")
                return {
                    'success': False,
                    'error': 'Alerta no encontrada'
                }
        except Exception as e:
            # print(f"❌ Error obteniendo alerta por ID: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_alert_for_user(self, alert_id, user_id):
        """Obtiene una alerta por ID si el usuario está en la lista de notificados
        o si es alert_manager de la misma empresa."""
        try:
            alert = self.alert_repo.get_alert_by_id(alert_id)

            if not alert:
                return {
                    'success': False,
                    'error': 'Alert not found'
                }

            # Verificar si el usuario está en la lista de números telefónicos
            user_is_authorized = False
            for user_info in alert.numeros_telefonicos:
                if user_info.get('usuario_id') == user_id:
                    user_is_authorized = True
                    break

            # Si no, verificar si es alert_manager de la misma empresa
            if not user_is_authorized:
                try:
                    from repositories.usuario_repository import UsuarioRepository
                    from repositories.empresa_repository import EmpresaRepository
                    from utils.role_utils import sanitize_roles, normalize_role_name

                    usuario = UsuarioRepository().find_by_id(user_id)
                    if usuario and usuario.empresa_id:
                        empresa = EmpresaRepository().find_by_id(usuario.empresa_id)
                        if empresa and empresa.nombre == alert.empresa_nombre:
                            roles_lookup = {r['nombre']: r for r in sanitize_roles(empresa.roles)}
                            rol_name = normalize_role_name(usuario.rol)
                            rol_info = roles_lookup.get(rol_name) if rol_name else None
                            if rol_info and rol_info.get('is_alert_manager'):
                                user_is_authorized = True
                except Exception:
                    pass

            if not user_is_authorized:
                return {
                    'success': False,
                    'error': 'Access denied',
                    'message': 'El usuario no está autorizado para ver esta alerta'
                }

            return {
                'success': True,
                'alert': alert.to_json()
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_alerts_by_empresa(self, empresa_nombre, page=1, limit=50):
        """Obtiene alertas por empresa"""
        try:
            alerts, total = self.alert_repo.get_alerts_by_empresa(empresa_nombre, page, limit)
            return {
                'success': True,
                'alerts': [alert.to_json() for alert in alerts],
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit
            }
        except Exception as e:
            # print(f"Error obteniendo alertas por empresa: {e}")
            return {
                'success': False,
                'error': str(e),
                'alerts': [],
                'total': 0
            }
    
    def get_active_alerts(self, page=1, limit=50):
        """Obtiene alertas activas"""
        try:
            alerts, total = self.alert_repo.get_active_alerts(page, limit)
            return {
                'success': True,
                'alerts': [alert.to_json() for alert in alerts],
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit
            }
        except Exception as e:
            # print(f"Error obteniendo alertas activas: {e}")
            return {
                'success': False,
                'error': str(e),
                'alerts': [],
                'total': 0
            }
    
    def get_unauthorized_alerts(self, page=1, limit=50):
        """Obtiene alertas no autorizadas"""
        try:
            alerts, total = self.alert_repo.get_unauthorized_alerts(page, limit)
            return {
                'success': True,
                'alerts': [alert.to_json() for alert in alerts],
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit
            }
        except Exception as e:
            # print(f"Error obteniendo alertas no autorizadas: {e}")
            return {
                'success': False,
                'error': str(e),
                'alerts': [],
                'total': 0
            }
    
    def get_inactive_alerts(self, page=1, limit=50):
        """Obtiene alertas inactivas/desactivadas"""
        try:
            alerts, total = self.alert_repo.get_inactive_alerts(page, limit)
            return {
                'success': True,
                'alerts': [alert.to_json() for alert in alerts],
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit
            }
        except Exception as e:
            # print(f"Error obteniendo alertas inactivas: {e}")
            return {
                'success': False,
                'error': str(e),
                'alerts': [],
                'total': 0
            }
    
    def get_inactive_alerts_by_empresa(self, empresa_id, page=1, limit=50):
        """Obtiene alertas inactivas/desactivadas por empresa específica"""
        try:
            print(f"🔍 DEBUG service.get_inactive_alerts_by_empresa:")
            print(f"  - empresa_id: {empresa_id}")
            print(f"  - page: {page}, limit: {limit}")
            
            alerts, total = self.alert_repo.get_inactive_alerts_by_empresa(empresa_id, page, limit)
            
            print(f"  📊 Respuesta del repositorio:")
            print(f"    - Total encontrado: {total}")
            print(f"    - Alertas obtenidas: {len(alerts)}")
            if alerts:
                print(f"    - Primera alerta ID: {alerts[0]._id if alerts else 'N/A'}")
            
            return {
                'success': True,
                'alerts': [alert.to_json() for alert in alerts],
                'total': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit
            }
        except Exception as e:
            # print(f"Error obteniendo alertas inactivas por empresa: {e}")
            return {
                'success': False,
                'error': str(e),
                'alerts': [],
                'total': 0
            }
    
    def authorize_alert(self, alert_id, usuario_id):
        """Autoriza una alerta"""
        try:
            success = self.alert_repo.authorize_alert(alert_id, usuario_id)
            if success:
                return {
                    'success': True,
                    'message': 'Alerta autorizada exitosamente'
                }
            else:
                return {
                    'success': False,
                    'error': 'No se pudo autorizar la alerta'
                }
        except Exception as e:
            # print(f"Error autorizando alerta: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def toggle_alert_status(self, alert_id):
        """Alterna el estado de una alerta"""
        try:
            success = self.alert_repo.toggle_alert_status(alert_id)
            if success:
                return {
                    'success': True,
                    'message': 'Estado de alerta actualizado exitosamente'
                }
            else:
                return {
                    'success': False,
                    'error': 'No se pudo actualizar el estado de la alerta'
                }
        except Exception as e:
            # print(f"Error cambiando estado de alerta: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_alert(self, alert_id):
        """Elimina una alerta"""
        try:
            success = self.alert_repo.delete_alert(alert_id)
            if success:
                return {
                    'success': True,
                    'message': 'Alerta eliminada exitosamente'
                }
            else:
                return {
                    'success': False,
                    'error': 'No se pudo eliminar la alerta'
                }
        except Exception as e:
            # print(f"Error eliminando alerta: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_alert_user_status(self, alert_id, usuario_id, updates):
        """
        Actualiza el estado de un usuario en una alerta.
        """
        try:
            alert, error = self.alert_repo.update_user_status_in_alert(alert_id, usuario_id, updates)
            if error:
                return {'success': False, 'error': error}
            
            return {'success': True, 'alert': alert.to_json()}
        except Exception as e:
            # print(f"Error updating alert user status: {e}")
            return {'success': False, 'error': str(e)}

    def get_alerts_stats(self):
        """Obtiene estadísticas de alertas"""
        try:
            stats = self.alert_repo.get_alerts_stats()
            return {
                'success': True,
                'stats': stats
            }
        except Exception as e:
            # print(f"Error obteniendo estadísticas: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': {}
            }
    
    def verify_empresa_sede(self, empresa_nombre, sede):
        """Verifica si existe una empresa con la sede especificada"""
        try:
            exists, message = self.alert_repo.verify_empresa_sede_exists(empresa_nombre, sede)
            usuarios = []
            
            if exists:
                usuarios = self.alert_repo.get_users_by_empresa_sede(empresa_nombre, sede)
            
            return {
                'success': exists,
                'message': message,
                'empresa': empresa_nombre,
                'sede': sede,
                'usuarios': usuarios
            }
        except Exception as e:
            # print(f"Error verificando empresa y sede: {e}")
            return {
                'success': False,
                'error': str(e),
                'empresa': empresa_nombre,
                'sede': sede,
                'usuarios': []
            }
    
    def get_alerts_active_by_empresa_sede(self, empresa_id, page=1, limit=5):
        """Obtiene alertas activas por empresa y sede"""
        try:
            alerts, total = self.alert_repo.get_active_alerts_by_empresa_sede(empresa_id, page, limit)
            return {
                'success': True,
                'data': [alert.to_json() for alert in alerts],
                'pagination': {
                    'total_pages': (total + limit - 1) // limit,
                    'current_page': page,
                    'total_items': total,
                    'has_next': page * limit < total,
                    'has_prev': page > 1
                }
            }
        except Exception as e:
            # print(f"Error obteniendo alertas activas por empresa y sede: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'pagination': {}
            }

    def _determine_priority(self, tipo_alerta, datos_hardware):
        """Determina la prioridad de la alerta basada en el tipo y datos"""
        try:
            # Prioridades por tipo de alerta
            priority_map = {
                'semaforo': 'media',
                'alarma': 'alta',
                'emergencia': 'critica',
                'mantenimiento': 'baja'
            }
            
            base_priority = priority_map.get(tipo_alerta.lower(), 'media')
            
            # Ajustar prioridad según datos del hardware
            if isinstance(datos_hardware, dict):
                alerta_value = datos_hardware.get('alerta', '').lower()
                
                # Prioridades específicas por tipo de alerta
                if 'critica' in alerta_value or 'roja' in alerta_value:
                    return 'critica'
                elif 'amarilla' in alerta_value or 'precaucion' in alerta_value:
                    return 'media'
                elif 'verde' in alerta_value or 'normal' in alerta_value:
                    return 'baja'
                elif 'naranja' in alerta_value:
                    return 'alta'
            
            return base_priority
            
        except Exception as e:
            # print(f"Error determinando prioridad: {e}")
            return 'media'  # prioridad por defecto
    
    # COMENTADO: Método obsoleto - La ubicación ahora viene incluida en el modelo MqttAlert
    # def _get_botonera_ubicacion(self, empresa_nombre, sede):
    #     """Obtiene información de ubicación de la botonera asociada a la empresa y sede"""
    #     try:
    #         print(f"🔍 Buscando botonera para empresa: {empresa_nombre}, sede: {sede}")
    #         
    #         # Buscar la empresa por nombre
    #         from repositories.empresa_repository import EmpresaRepository
    #         empresa_repo = EmpresaRepository()
    #         empresa = empresa_repo.find_by_nombre(empresa_nombre)
    #         
    #         if not empresa:
    #             print(f"❌ Empresa no encontrada: {empresa_nombre}")
    #             return {
    #                 'direccion': None,
    #                 'direccion_url': None,
    #                 'direccion_open_maps': None,
    #                 'error': 'Empresa no encontrada'
    #             }
    #         
    #         # Buscar botonera de esa empresa y sede
    #         from repositories.hardware_repository import HardwareRepository
    #         hardware_repo = HardwareRepository()
    #         
    #         botoneras = hardware_repo.find_with_filters({
    #             'empresa_id': empresa._id,
    #             'sede': sede,
    #             'activa': True
    #         })
    #         
    #         # Filtrar solo botoneras
    #         botonera = None
    #         for hw in botoneras:
    #             if hw.tipo.upper() == 'BOTONERA':
    #                 botonera = hw
    #                 break
    #         
    #         if botonera:
    #             print(f"✅ Botonera encontrada: {botonera.nombre}")
    #             return {
    #                 'direccion': botonera.direccion,
    #                 'direccion_url': botonera.direccion_url,  # Google Maps
    #                 'direccion_open_maps': getattr(botonera, 'direccion_open_maps', None),  # OpenStreetMap
    #                 'hardware_nombre': botonera.nombre,
    #                 'hardware_id': str(botonera._id)
    #             }
    #         else:
    #             print(f"❌ No se encontró botonera para empresa {empresa_nombre} en sede {sede}")
    #             return {
    #                 'direccion': None,
    #                 'direccion_url': None,
    #                 'direccion_open_maps': None,
    #                 'error': 'Botonera no encontrada para esta empresa y sede'
    #             }
    #             
    #     except Exception as e:
    #         print(f"❌ Error buscando ubicación de botonera: {e}")
    #         return {
    #             'direccion': None,
    #             'direccion_url': None,
    #             'direccion_open_maps': None,
    #             'error': f'Error interno: {str(e)}'
    #         }
