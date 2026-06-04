from bson import ObjectId
import bcrypt
from models.empresa import Empresa
from repositories.empresa_repository import EmpresaRepository
from repositories.usuario_repository import UsuarioRepository
from utils.whatsapp_service_client import whatsapp_client
from utils.role_utils import sanitize_roles

class EmpresaService:
    def __init__(self):
        self.empresa_repository = EmpresaRepository()
        self.usuario_repository = UsuarioRepository()

    def _roles_changed(self, prev_roles, new_roles) -> bool:
        """Compara roles previos vs nuevos. Devuelve True si hay diferencia significativa."""
        prev = {r['nombre']: (r.get('is_creator', False), r.get('is_alert_manager', False))
                for r in sanitize_roles(prev_roles)}
        curr = {r['nombre']: (r.get('is_creator', False), r.get('is_alert_manager', False))
                for r in sanitize_roles(new_roles)}
        return prev != curr

    def _invalidate_whatsapp_cache_for_empresa(self, empresa_id) -> None:
        """Borra del cache WhatsApp a todos los usuarios de la empresa (fire-and-forget)"""
        try:
            usuarios = self.usuario_repository.find_by_empresa(empresa_id) or []
            for usr in usuarios:
                telefono = getattr(usr, 'telefono', None)
                if telefono:
                    try:
                        whatsapp_client.delete_number(telefono)
                    except Exception:
                        pass
        except Exception:
            pass
    
    def create_empresa(self, empresa_data, super_admin_id):
        """Crea una nueva empresa con validaciones"""
        try:
            # Validar que el super_admin_id sea válido
            if not super_admin_id:
                return {
                    'success': False,
                    'errors': ['El ID del super admin es obligatorio']
                }
            
            # Convertir super_admin_id a ObjectId si es string
            if isinstance(super_admin_id, str):
                try:
                    super_admin_id = ObjectId(super_admin_id)
                except Exception:
                    return {
                        'success': False,
                        'errors': ['El ID del super admin no es válido']
                    }
            
            password = empresa_data.get('password')
            if not password:
                return {'success': False, 'errors': ['La contraseña es obligatoria']}

            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Validar tipo_empresa_id si se proporciona
            tipo_empresa_id = empresa_data.get('tipo_empresa_id')
            if tipo_empresa_id:
                try:
                    if isinstance(tipo_empresa_id, str):
                        tipo_empresa_id = ObjectId(tipo_empresa_id)
                except Exception:
                    return {
                        'success': False,
                        'errors': ['El ID del tipo de empresa no es válido']
                    }

            empresa = Empresa(
                nombre=empresa_data.get('nombre'),
                descripcion=empresa_data.get('descripcion'),
                ubicacion=empresa_data.get('ubicacion'),
                creado_por=super_admin_id,
                username=empresa_data.get('username'),
                email=empresa_data.get('email'),
                password_hash=password_hash,
                sedes=empresa_data.get('sedes'),
                roles=empresa_data.get('roles', []),
                tipo_empresa_id=tipo_empresa_id
            )
            
            # Validar datos
            validation_errors = empresa.validate()
            if validation_errors:
                return {
                    'success': False,
                    'errors': validation_errors
                }
            
            # Verificar duplicados
            if self.empresa_repository.find_by_nombre(empresa.nombre):
                return {
                    'success': False,
                    'errors': ['Ya existe una empresa con ese nombre']
                }
            if self.empresa_repository.find_by_username(empresa.username):
                return {
                    'success': False,
                    'errors': ['El nombre de usuario ya está en uso']
                }
            if self.empresa_repository.find_by_email(empresa.email):
                return {
                    'success': False,
                    'errors': ['El correo ya está en uso']
                }
            
            # Crear empresa
            created_empresa = self.empresa_repository.create(empresa)
            return {
                'success': True,
                'data': created_empresa.to_json(),
                'message': 'Empresa creada exitosamente'
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def get_empresa_by_id(self, empresa_id):
        """Obtiene una empresa por ID"""
        try:
            empresa = self.empresa_repository.find_by_id(empresa_id)
            if empresa:
                return {
                    'success': True,
                    'data': empresa.to_json()
                }
            else:
                return {
                    'success': False,
                    'errors': ['Empresa no encontrada']
                }
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def get_all_empresas(self, include_inactive=False):
        """Obtiene todas las empresas"""
        try:
            empresas = self.empresa_repository.find_all(include_inactive)
            empresas_json = [empresa.to_json() for empresa in empresas]
            return {
                'success': True,
                'data': empresas_json,
                'count': len(empresas_json)
            }
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def get_empresas_by_creador(self, super_admin_id):
        """Obtiene empresas creadas por un super admin específico"""
        try:
            empresas = self.empresa_repository.find_by_creador(super_admin_id)
            empresas_json = [empresa.to_json() for empresa in empresas]
            return {
                'success': True,
                'data': empresas_json,
                'count': len(empresas_json)
            }
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def get_empresa_by_id_including_inactive(self, empresa_id):
        """Obtiene una empresa por ID incluyendo inactivas (para admins)"""
        try:
            empresa = self.empresa_repository.find_by_id_including_inactive(empresa_id)
            if empresa:
                return {
                    'success': True,
                    'data': empresa.to_json()
                }
            else:
                return {
                    'success': False,
                    'errors': ['Empresa no encontrada']
                }
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def update_empresa(self, empresa_id, empresa_data, super_admin_id=None):
        """Actualiza una empresa existente"""
        try:
            # Verificar si la empresa existe (incluyendo inactivas)
            existing_empresa = self.empresa_repository.find_by_id_including_inactive(empresa_id)
            if not existing_empresa:
                return {
                    'success': False,
                    'errors': ['Empresa no encontrada']
                }
            
            # Si se proporciona super_admin_id, verificar que sea el creador
            if super_admin_id:
                if isinstance(super_admin_id, str):
                    super_admin_id = ObjectId(super_admin_id)
                
                if existing_empresa.creado_por != super_admin_id:
                    return {
                        'success': False,
                        'errors': ['No tienes permisos para modificar esta empresa']
                    }
            
            # Preparar password
            new_password = empresa_data.get('password')
            password_hash = existing_empresa.password_hash
            if new_password:
                password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Validar tipo_empresa_id si se proporciona para actualización
            tipo_empresa_id = empresa_data.get('tipo_empresa_id', existing_empresa.tipo_empresa_id)
            if tipo_empresa_id and isinstance(tipo_empresa_id, str):
                try:
                    tipo_empresa_id = ObjectId(tipo_empresa_id)
                except Exception:
                    return {
                        'success': False,
                        'errors': ['El ID del tipo de empresa no es válido']
                    }

            # Crear objeto Empresa con datos actualizados
            updated_empresa = Empresa(
                nombre=empresa_data.get('nombre', existing_empresa.nombre),
                descripcion=empresa_data.get('descripcion', existing_empresa.descripcion),
                ubicacion=empresa_data.get('ubicacion', existing_empresa.ubicacion),
                creado_por=existing_empresa.creado_por,
                username=empresa_data.get('username', existing_empresa.username),
                email=empresa_data.get('email', existing_empresa.email),
                password_hash=password_hash,
                sedes=empresa_data.get('sedes', existing_empresa.sedes),
                roles=empresa_data.get('roles', existing_empresa.roles),
                tipo_empresa_id=tipo_empresa_id,
                _id=existing_empresa._id,
                activa=existing_empresa.activa,
            )

            # Mantener datos originales
            updated_empresa.fecha_creacion = existing_empresa.fecha_creacion
            updated_empresa.last_login = existing_empresa.last_login
            
            # Validar datos
            validation_errors = updated_empresa.validate()
            if validation_errors:
                return {
                    'success': False,
                    'errors': validation_errors
                }
            
            # Verificar si el nombre ya existe (solo si cambió)
            if updated_empresa.nombre.lower() != existing_empresa.nombre.lower():
                nombre_exists = self.empresa_repository.find_by_nombre_excluding_id(
                    updated_empresa.nombre, empresa_id
                )
                if nombre_exists:
                    return {
                        'success': False,
                        'errors': ['Ya existe una empresa con ese nombre']
                    }

            if updated_empresa.username != existing_empresa.username:
                username_exists = self.empresa_repository.find_by_username_excluding_id(
                    updated_empresa.username, empresa_id
                )
                if username_exists:
                    return {
                        'success': False,
                        'errors': ['El nombre de usuario ya está en uso']
                    }

            if updated_empresa.email != existing_empresa.email:
                email_exists = self.empresa_repository.find_by_email_excluding_id(
                    updated_empresa.email, empresa_id
                )
                if email_exists:
                    return {
                        'success': False,
                        'errors': ['El correo ya está en uso']
                    }
            
            # Actualizar empresa
            result = self.empresa_repository.update(empresa_id, updated_empresa)
            if result:
                # Si los roles cambiaron, invalidar cache WhatsApp de los usuarios de la empresa
                if self._roles_changed(existing_empresa.roles, updated_empresa.roles):
                    self._invalidate_whatsapp_cache_for_empresa(result._id)
                return {
                    'success': True,
                    'data': result.to_json(),
                    'message': 'Empresa actualizada exitosamente'
                }
            else:
                return {
                    'success': False,
                    'errors': ['Error actualizando empresa']
                }
                
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def delete_empresa(self, empresa_id, super_admin_id=None):
        """Elimina una empresa (soft delete)"""
        try:
            # Verificar si la empresa existe (incluyendo inactivas)
            existing_empresa = self.empresa_repository.find_by_id_including_inactive(empresa_id)
            if not existing_empresa:
                return {
                    'success': False,
                    'errors': ['Empresa no encontrada']
                }
            
            # Si se proporciona super_admin_id, verificar que sea el creador
            if super_admin_id:
                if isinstance(super_admin_id, str):
                    super_admin_id = ObjectId(super_admin_id)
                
                if existing_empresa.creado_por != super_admin_id:
                    return {
                        'success': False,
                        'errors': ['No tienes permisos para eliminar esta empresa']
                    }
            
            # Eliminar empresa (soft delete)
            deleted = self.empresa_repository.soft_delete(empresa_id)
            if deleted:
                return {
                    'success': True,
                    'message': 'Empresa eliminada correctamente'
                }
            else:
                return {
                    'success': False,
                    'errors': ['Error eliminando empresa']
                }
                
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def toggle_empresa_status(self, empresa_id, activa, super_admin_id=None):
        """Activar o desactivar empresa"""
        try:
            # Verificar si la empresa existe (incluyendo inactivas)
            existing_empresa = self.empresa_repository.find_by_id_including_inactive(empresa_id)
            if not existing_empresa:
                return {
                    'success': False,
                    'errors': ['Empresa no encontrada']
                }
            
            # Si se proporciona super_admin_id, verificar que sea el creador
            if super_admin_id:
                if isinstance(super_admin_id, str):
                    super_admin_id = ObjectId(super_admin_id)
                
                if existing_empresa.creado_por != super_admin_id:
                    return {
                        'success': False,
                        'errors': ['No tienes permisos para modificar esta empresa']
                    }
            
            # Actualizar solo el campo activa
            existing_empresa.activa = activa
            existing_empresa.update_timestamp()
            
            updated = self.empresa_repository.update(empresa_id, existing_empresa)
            if updated:
                status_text = "activada" if activa else "desactivada"
                return {
                    'success': True, 
                    'data': updated.to_json(),
                    'message': f'Empresa {status_text} exitosamente'
                }
            return {
                'success': False, 
                'errors': ['Error al actualizar el estado de la empresa']
            }
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def search_empresas_by_ubicacion(self, ubicacion):
        """Busca empresas por ubicación"""
        try:
            empresas = self.empresa_repository.search_by_ubicacion(ubicacion)
            empresas_json = [empresa.to_json() for empresa in empresas]
            return {
                'success': True,
                'data': empresas_json,
                'count': len(empresas_json)
            }
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def get_empresa_stats(self):
        """Obtiene estadísticas de empresas"""
        try:
            total_activas = self.empresa_repository.count(include_inactive=False)
            total_inactivas = self.empresa_repository.count(include_inactive=True) - total_activas
            
            return {
                'success': True,
                'data': {
                    'total_activas': total_activas,
                    'total_inactivas': total_inactivas,
                    'total_general': total_activas + total_inactivas
                }
            }
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
    
    def get_empresa_statistics(self, empresa_id):
        """Obtiene estadísticas específicas de una empresa"""
        try:
            # Verificar que la empresa existe
            empresa = self.empresa_repository.find_by_id(empresa_id)
            if not empresa:
                return {
                    'success': False,
                    'errors': ['Empresa no encontrada']
                }
            
            # Importar servicios necesarios
            from services.usuario_service import UsuarioService
            from services.hardware_service import HardwareService
            from services.mqtt_alert_service import MqttAlertService
            from datetime import datetime, timedelta
            
            usuario_service = UsuarioService()
            hardware_service = HardwareService()
            alert_service = MqttAlertService()
            
            # Obtener estadísticas de usuarios
            usuarios_result = usuario_service.get_usuarios_by_empresa_including_inactive(empresa_id)
            usuarios_stats = {
                'total_usuarios': 0,
                'usuarios_activos': 0,
                'usuarios_inactivos': 0
            }
            
            if usuarios_result.get('success'):
                usuarios_data = usuarios_result.get('data', [])
                usuarios_stats = {
                    'total_usuarios': len(usuarios_data),
                    'usuarios_activos': len([u for u in usuarios_data if u.get('activo', True)]),
                    'usuarios_inactivos': len([u for u in usuarios_data if not u.get('activo', True)])
                }
            
            # Obtener estadísticas de hardware
            hardware_result = hardware_service.get_hardware_by_empresa_including_inactive(empresa_id)
            hardware_stats = {
                'total_hardware': 0,
                'hardware_activo': 0,
                'hardware_inactivo': 0,
                'por_tipo': {}
            }
            
            if hardware_result.get('success'):
                hardware_data = hardware_result.get('data', [])
                
                # Calcular distribución por tipo
                por_tipo = {}
                for hardware in hardware_data:
                    tipo = hardware.get('tipo', 'Unknown')
                    por_tipo[tipo] = por_tipo.get(tipo, 0) + 1
                
                hardware_stats = {
                    'total_hardware': len(hardware_data),
                    'hardware_activo': len([h for h in hardware_data if h.get('activa', True)]),
                    'hardware_inactivo': len([h for h in hardware_data if not h.get('activa', True)]),
                    'por_tipo': por_tipo
                }
            
            # Obtener estadísticas de alertas
            alertas_stats = {
                'total_alertas': 0,
                'alertas_activas': 0,
                'alertas_inactivas': 0,
                'alertas_recientes_30d': 0,
                'alertas_por_prioridad': {
                    'critica': 0,
                    'alta': 0,
                    'media': 0,
                    'baja': 0
                }
            }
            
            try:
                # Obtener alertas por nombre de empresa
                alertas_result = alert_service.get_alerts_by_empresa(empresa.nombre, page=1, limit=1000)
                if alertas_result.get('success'):
                    alertas_data = alertas_result.get('alerts', [])
                    
                    # Estadísticas básicas
                    alertas_stats['total_alertas'] = len(alertas_data)
                    alertas_stats['alertas_activas'] = len([a for a in alertas_data if a.get('activo', False)])
                    alertas_stats['alertas_inactivas'] = len([a for a in alertas_data if not a.get('activo', False)])
                    
                    # Estadísticas por prioridad
                    for alerta in alertas_data:
                        prioridad = alerta.get('prioridad', 'media').lower()
                        if prioridad in alertas_stats['alertas_por_prioridad']:
                            alertas_stats['alertas_por_prioridad'][prioridad] += 1
                    
                    # Alertas de los últimos 30 días
                    hace_30_dias = datetime.utcnow() - timedelta(days=30)
                    
                    for alerta in alertas_data:
                        fecha_creacion_str = alerta.get('fecha_creacion')
                        if fecha_creacion_str:
                            try:
                                # Manejar diferentes formatos de fecha
                                if isinstance(fecha_creacion_str, str):
                                    if 'T' in fecha_creacion_str:
                                        fecha_creacion = datetime.fromisoformat(fecha_creacion_str.replace('Z', '+00:00'))
                                    else:
                                        fecha_creacion = datetime.fromisoformat(fecha_creacion_str)
                                else:
                                    # Si es un objeto datetime directamente
                                    fecha_creacion = fecha_creacion_str
                                
                                if fecha_creacion >= hace_30_dias:
                                    alertas_stats['alertas_recientes_30d'] += 1
                            except (ValueError, TypeError, AttributeError):
                                continue
                    
            except Exception as e:
                # print(f"Error obteniendo estadísticas de alertas: {e}")
                # Mantener las estadísticas vacías si hay error
                pass
            
            return {
                'success': True,
                'data': {
                    'empresa': {
                        'id': str(empresa._id),
                        'nombre': empresa.nombre,
                        'activa': empresa.activa,
                        'fecha_creacion': empresa.fecha_creacion.isoformat() if empresa.fecha_creacion else None
                    },
                    'usuarios': usuarios_stats,
                    'hardware': hardware_stats,
                    'alertas': alertas_stats
                }
            }
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)]
            }
