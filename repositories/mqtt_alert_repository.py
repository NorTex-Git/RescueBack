from core.database import Database
from models.mqtt_alert import MqttAlert
from bson import ObjectId
from datetime import datetime

from utils.role_utils import sanitize_roles, normalize_role_name

class MqttAlertRepository:
    """Repositorio para operaciones de alertas MQTT"""
    
    def __init__(self):
        self.db = Database().get_database()
        self.collection = self.db.mqtt_alerts
    
    def create_alert(self, alert):
        """Crea una nueva alerta MQTT"""
        try:
            alert.normalize_data()
            result = self.collection.insert_one(alert.to_dict())
            alert._id = result.inserted_id
            return alert
        except Exception as e:
            # print(f"Error creando alerta MQTT: {e}")
            raise e
    
    def get_alert_by_id(self, alert_id):
        """Obtiene una alerta por su ID"""
        try:
            # print(f"🏦  Repositorio: Buscando alerta con ID: {alert_id}")
            # print(f"🔧 Convirtiendo a ObjectId...")
            object_id = ObjectId(alert_id)
            # print(f"✅ ObjectId creado: {object_id}")
            
            # print(f"🔍 Ejecutando query en MongoDB...")
            alert_data = self.collection.find_one({'_id': object_id})
            # print(f"📄 Datos obtenidos de MongoDB: {alert_data}")
            
            if alert_data:
                # print(f"✅ Datos encontrados, creando objeto MqttAlert...")
                alert_obj = MqttAlert.from_dict(alert_data)
                # print(f"🎯 Objeto MqttAlert creado: {alert_obj}")
                return alert_obj
            else:
                # print(f"❌ No se encontraron datos para este ID")
                return None
        except Exception as e:
            # print(f"❌ Error obteniendo alerta por ID: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_all_alerts(self, page=1, limit=50):
        """Obtiene todas las alertas con paginación"""
        try:
            skip = (page - 1) * limit
            alerts_data = self.collection.find().sort('fecha_creacion', -1).skip(skip).limit(limit)
            alerts = [MqttAlert.from_dict(alert_data) for alert_data in alerts_data]
            total = self.collection.count_documents({})
            return alerts, total
        except Exception as e:
            # print(f"Error obteniendo alertas: {e}")
            return [], 0
    
    def get_alerts_by_empresa(self, empresa_nombre, page=1, limit=50):
        """Obtiene alertas por empresa"""
        try:
            skip = (page - 1) * limit
            query = {'empresa_nombre': empresa_nombre}
            alerts_data = self.collection.find(query).sort('fecha_creacion', -1).skip(skip).limit(limit)
            alerts = [MqttAlert.from_dict(alert_data) for alert_data in alerts_data]
            total = self.collection.count_documents(query)
            return alerts, total
        except Exception as e:
            # print(f"Error obteniendo alertas por empresa: {e}")
            return [], 0
    
    def get_alerts_by_sede(self, empresa_nombre, sede, page=1, limit=50):
        """Obtiene alertas por empresa y sede"""
        try:
            skip = (page - 1) * limit
            query = {'empresa_nombre': empresa_nombre, 'sede': sede}
            alerts_data = self.collection.find(query).sort('fecha_creacion', -1).skip(skip).limit(limit)
            alerts = [MqttAlert.from_dict(alert_data) for alert_data in alerts_data]
            total = self.collection.count_documents(query)
            return alerts, total
        except Exception as e:
            # print(f"Error obteniendo alertas por sede: {e}")
            return [], 0
    
    def get_active_alerts(self, page=1, limit=50):
        """Obtiene alertas activas"""
        try:
            skip = (page - 1) * limit
            query = {'activo': True}
            alerts_data = self.collection.find(query).sort('fecha_creacion', -1).skip(skip).limit(limit)
            alerts = [MqttAlert.from_dict(alert_data) for alert_data in alerts_data]
            total = self.collection.count_documents(query)
            return alerts, total
        except Exception as e:
            # print(f"Error obteniendo alertas activas: {e}")
            return [], 0
    
    def get_unauthorized_alerts(self, page=1, limit=50):
        """Obtiene alertas no autorizadas"""
        try:
            skip = (page - 1) * limit
            query = {'autorizado': False}
            alerts_data = self.collection.find(query).sort('fecha_creacion', -1).skip(skip).limit(limit)
            alerts = [MqttAlert.from_dict(alert_data) for alert_data in alerts_data]
            total = self.collection.count_documents(query)
            return alerts, total
        except Exception as e:
            # print(f"Error obteniendo alertas no autorizadas: {e}")
            return [], 0
    
    def get_inactive_alerts(self, page=1, limit=50):
        """Obtiene alertas desactivadas/inactivas"""
        try:
            skip = (page - 1) * limit
            query = {'activo': False}
            alerts_data = self.collection.find(query).sort('fecha_creacion', -1).skip(skip).limit(limit)
            alerts = [MqttAlert.from_dict(alert_data) for alert_data in alerts_data]
            total = self.collection.count_documents(query)
            return alerts, total
        except Exception as e:
            # print(f"Error obteniendo alertas inactivas: {e}")
            return [], 0
    
    def get_inactive_alerts_by_empresa(self, empresa_id, page=1, limit=50):
        """Obtiene alertas desactivadas/inactivas por empresa específica"""
        try:
            print(f"🔍 DEBUG repo.get_inactive_alerts_by_empresa:")
            print(f"  - empresa_id: {empresa_id}")
            print(f"  - page: {page}, limit: {limit}")
            
            skip = (page - 1) * limit
            
            # Primero buscar la empresa por ID para obtener su nombre
            empresa = self.db.empresas.find_one({'_id': ObjectId(empresa_id)})
            if not empresa:
                print(f"  ❌ Empresa no encontrada con ID: {empresa_id}")
                return [], 0
            
            empresa_nombre = empresa['nombre']
            print(f"  ✅ Empresa encontrada: {empresa_nombre}")
            
            # Buscar alertas por empresa_nombre y activo=False
            query = {'empresa_nombre': empresa_nombre, 'activo': False}
            print(f"  🔍 Query MongoDB: {query}")
            print(f"  🔍 Skip: {skip}, Limit: {limit}")
            
            alerts_data = self.collection.find(query).sort('fecha_creacion', -1).skip(skip).limit(limit)
            alerts_list = list(alerts_data)  # Convertir cursor a lista
            print(f"  📊 Documentos encontrados: {len(alerts_list)}")
            
            alerts = []
            for i, alert_data in enumerate(alerts_list):
                try:
                    alert_obj = MqttAlert.from_dict(alert_data)
                    alerts.append(alert_obj)
                    if i == 0:  # Solo mostrar la primera para debug
                        print(f"  📄 Primera alerta: ID={alert_obj._id}, activo={alert_obj.activo}")
                except Exception as e:
                    print(f"  ⚠️ Error convirtiendo alerta {i}: {e}")
            
            total = self.collection.count_documents(query)
            print(f"  📊 Total en DB: {total}, Convertidos a objetos: {len(alerts)}")
            
            return alerts, total
        except Exception as e:
            # print(f"Error obteniendo alertas inactivas por empresa: {e}")
            return [], 0
    
    def update_alert(self, alert_id, alert):
        """Actualiza una alerta"""
        try:
            alert.normalize_data()
            alert.update_timestamp()
            update_data = alert.to_dict()
            del update_data['_id']  # No actualizar el ID
            
            result = self.collection.update_one(
                {'_id': ObjectId(alert_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            # print(f"Error actualizando alerta: {e}")
            return False
    
    def authorize_alert(self, alert_id, usuario_id):
        """Autoriza una alerta"""
        try:
            result = self.collection.update_one(
                {'_id': ObjectId(alert_id)},
                {
                    '$set': {
                        'autorizado': True,
                        'usuario_autorizador': ObjectId(usuario_id) if usuario_id else None,
                        'fecha_autorizacion': datetime.utcnow(),
                        'fecha_actualizacion': datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            # print(f"Error autorizando alerta: {e}")
            return False
    
    def toggle_alert_status(self, alert_id):
        """Alterna el estado activo de una alerta"""
        try:
            alert = self.get_alert_by_id(alert_id)
            if not alert:
                return False
            
            new_status = not alert.activo
            result = self.collection.update_one(
                {'_id': ObjectId(alert_id)},
                {
                    '$set': {
                        'activo': new_status,
                        'fecha_actualizacion': datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            # print(f"Error cambiando estado de alerta: {e}")
            return False
    
    def delete_alert(self, alert_id):
        """Elimina una alerta"""
        try:
            result = self.collection.delete_one({'_id': ObjectId(alert_id)})
            return result.deleted_count > 0
        except Exception as e:
            # print(f"Error eliminando alerta: {e}")
            return False
    
    def update_user_status_in_alert(self, alert_id, usuario_id, updates):
        """
        Actualiza el estado de un usuario en la lista de numeros_telefonicos de una alerta.
        """
        try:
            # Filtrar solo las llaves permitidas para actualizar
            allowed_keys = ['disponible', 'embarcado']
            update_fields = {f"numeros_telefonicos.$[elem].{key}": value for key, value in updates.items() if key in allowed_keys}

            if not update_fields:
                return None, "No valid fields to update"

            result = self.collection.update_one(
                {'_id': ObjectId(alert_id)},
                {'$set': update_fields},
                array_filters=[{'elem.usuario_id': usuario_id}]
            )

            if result.modified_count > 0:
                return self.get_alert_by_id(alert_id), None
            else:
                # Check if the alert and user exist
                alert = self.collection.find_one({'_id': ObjectId(alert_id)})
                if not alert:
                    return None, "Alert not found"
                
                user_in_alert = any(user['usuario_id'] == usuario_id for user in alert.get('numeros_telefonicos', []))
                if not user_in_alert:
                    return None, "User not found in this alert"
                
                return None, "No changes were made"

        except Exception as e:
            # print(f"Error updating user status in alert: {e}")
            return None, str(e)

    def get_alerts_stats(self):
        """Obtiene estadísticas de alertas"""
        try:
            total = self.collection.count_documents({})
            active = self.collection.count_documents({'activo': True})
            authorized = self.collection.count_documents({'autorizado': True})
            unauthorized = self.collection.count_documents({'autorizado': False})
            
            return {
                'total': total,
                'active': active,
                'inactive': total - active,
                'authorized': authorized,
                'unauthorized': unauthorized
            }
        except Exception as e:
            # print(f"Error obteniendo estadísticas de alertas: {e}")
            return {
                'total': 0,
                'active': 0,
                'inactive': 0,
                'authorized': 0,
                'unauthorized': 0
            }
    
    def verify_empresa_sede_exists(self, empresa_nombre, sede):
        """Verifica si existe una empresa con la sede especificada"""
        try:
            # Buscar en la colección de empresas
            empresa = self.db.empresas.find_one({'nombre': empresa_nombre})
            if not empresa:
                return False, "Empresa no encontrada"
            
            # Verificar si la sede existe en la empresa
            if 'sedes' in empresa and isinstance(empresa['sedes'], list):
                if sede in empresa['sedes']:
                    return True, "Empresa y sede válidas"
                else:
                    return False, "Sede no encontrada en la empresa"
            else:
                # Si no hay sedes específicas, considerar válida cualquier sede
                return True, "Empresa válida"
        except Exception as e:
            # print(f"Error verificando empresa y sede: {e}")
            return False, "Error en la verificación"
    
    def get_users_by_empresa_sede(self, empresa_nombre, sede):
        """Obtiene usuarios por empresa y sede"""
        try:
            # Buscar la empresa primero
            empresa = self.db.empresas.find_one({'nombre': empresa_nombre})
            if not empresa:
                return []
            
            # Catalogar roles de la empresa
            catalogo_roles = sanitize_roles(empresa.get('roles'))
            roles_lookup = {
                entry['nombre']: entry for entry in catalogo_roles
            }

            # Buscar usuarios de esa empresa y sede
            query = {
                'empresa_id': empresa['_id'],
                'sede': sede,
                'activo': True
            }
            
            usuarios_cursor = self.db.usuarios.find(query, {
                'nombre': 1,
                'telefono': 1,
                'email': 1,
                'rol': 1,
                'especialidades': 1
            })

            usuarios = []
            for usuario in usuarios_cursor:
                rol_name = normalize_role_name(usuario.get('rol')) or None
                rol_info = roles_lookup.get(rol_name) if rol_name else None
                usuario['rol_detalle'] = {
                    'nombre': rol_info['nombre'] if rol_info else rol_name,
                    'is_creator': rol_info['is_creator'] if rol_info else False,
                    'is_alert_manager': rol_info.get('is_alert_manager', False) if rol_info else False
                }
                usuarios.append(usuario)

            return usuarios
        except Exception as e:
            # print(f"Error obteniendo usuarios por empresa y sede: {e}")
            return []

    def get_alert_managers_by_empresa(self, empresa_nombre):
        """Obtiene todos los usuarios con rol is_alert_manager de una empresa (todas las sedes)"""
        try:
            empresa = self.db.empresas.find_one({'nombre': empresa_nombre})
            if not empresa:
                return []

            catalogo_roles = sanitize_roles(empresa.get('roles'))
            manager_role_names = {
                entry['nombre'] for entry in catalogo_roles
                if entry.get('is_alert_manager')
            }

            if not manager_role_names:
                return []

            roles_lookup = {entry['nombre']: entry for entry in catalogo_roles}

            usuarios_cursor = self.db.usuarios.find({
                'empresa_id': empresa['_id'],
                'activo': True
            }, {
                'nombre': 1,
                'telefono': 1,
                'email': 1,
                'rol': 1,
                'sede': 1
            })

            managers = []
            for usuario in usuarios_cursor:
                rol_name = normalize_role_name(usuario.get('rol')) or None
                if not rol_name or rol_name not in manager_role_names:
                    continue
                rol_info = roles_lookup.get(rol_name)
                usuario['rol_detalle'] = {
                    'nombre': rol_info['nombre'] if rol_info else rol_name,
                    'is_creator': rol_info['is_creator'] if rol_info else False,
                    'is_alert_manager': True
                }
                managers.append(usuario)

            return managers
        except Exception:
            return []

    def get_latest_active_alert_per_sede(self, empresa_nombre):
        """Devuelve la última alerta activa de cada sede de la empresa"""
        try:
            pipeline = [
                {'$match': {'empresa_nombre': empresa_nombre, 'activo': True}},
                {'$sort': {'fecha_creacion': -1}},
                {'$group': {
                    '_id': '$sede',
                    'alert': {'$first': '$$ROOT'}
                }}
            ]
            results = list(self.collection.aggregate(pipeline))
            return [r['alert'] for r in results]
        except Exception:
            return []

    def verify_hardware_exists(self, hardware_nombre):
        """Verifica si existe un hardware con el nombre especificado"""
        try:
            # Buscar en la colección de hardware
            hardware = self.db.hardware.find_one({
                'nombre': hardware_nombre,
                'activa': True
            })
            
            if hardware:
                return True, hardware, "Hardware encontrado"
            else:
                return False, None, "Hardware no encontrado"
                
        except Exception as e:
            # print(f"Error verificando hardware: {e}")
            return False, None, f"Error en la verificación: {e}"
    
    def get_full_verification_info(self, hardware_nombre):
        """Obtiene información completa de verificación: hardware, empresa y usuarios"""
        try:
            # Verificar hardware primero
            hardware_exists, hardware_data, hardware_message = self.verify_hardware_exists(hardware_nombre)
            
            if not hardware_exists:
                return {
                    'hardware_exists': False,
                    'hardware_message': hardware_message,
                    'empresa_exists': False,
                    'sede_exists': False,
                    'usuarios': [],
                    'hardware_data': None
                }
            
            # Si el hardware existe, obtener empresa y sede
            empresa_id = hardware_data.get('empresa_id')
            sede = hardware_data.get('sede')
            
            # Buscar empresa
            empresa = self.db.empresas.find_one({'_id': empresa_id})
            if not empresa:
                return {
                    'hardware_exists': True,
                    'hardware_message': hardware_message,
                    'empresa_exists': False,
                    'sede_exists': False,
                    'usuarios': [],
                    'hardware_data': hardware_data
                }
            
            # Verificar sede
            sede_exists = True
            if 'sedes' in empresa and isinstance(empresa['sedes'], list):
                sede_exists = sede in empresa['sedes']
            
            # Obtener usuarios
            usuarios = []
            if sede_exists:
                usuarios = self.get_users_by_empresa_sede(empresa['nombre'], sede)
            
            return {
                'hardware_exists': True,
                'hardware_message': hardware_message,
                'empresa_exists': True,
                'sede_exists': sede_exists,
                'usuarios': usuarios,
                'hardware_data': hardware_data,
                'empresa_data': empresa
            }
            
        except Exception as e:
            # print(f"Error en verificación completa: {e}")
            return {
                'hardware_exists': False,
                'hardware_message': f"Error: {e}",
                'empresa_exists': False,
                'sede_exists': False,
                'usuarios': [],
                'hardware_data': None
            }
    
    def get_alerts_by_hardware_id(self, hardware_id, page=1, limit=50):
        """Obtiene alertas por ID de hardware"""
        try:
            skip = (page - 1) * limit
            query = {'hardware_id': ObjectId(hardware_id)}
            alerts_data = self.collection.find(query).sort('fecha_creacion', -1).skip(skip).limit(limit)
            alerts = [MqttAlert.from_dict(alert_data) for alert_data in alerts_data]
            total = self.collection.count_documents(query)
            return alerts, total
        except Exception as e:
            # print(f"Error obteniendo alertas por hardware_id: {e}")
            return [], 0
    
    def get_alerts_by_hardware_name(self, hardware_nombre, page=1, limit=50):
        """Obtiene alertas por nombre de hardware"""
        try:
            skip = (page - 1) * limit
            query = {'hardware_nombre': hardware_nombre}
            alerts_data = self.collection.find(query).sort('fecha_creacion', -1).skip(skip).limit(limit)
            alerts = [MqttAlert.from_dict(alert_data) for alert_data in alerts_data]
            total = self.collection.count_documents(query)
            return alerts, total
        except Exception as e:
            # print(f"Error obteniendo alertas por hardware_nombre: {e}")
            return [], 0
    
    def get_active_alerts_by_empresa_sede(self, empresa_id, page=1, limit=5):
        """Obtiene alertas activas por empresa y sede"""
        try:
            skip = (page - 1) * limit
            
            # Primero buscar la empresa por ID para obtener su nombre
            empresa = self.db.empresas.find_one({'_id': ObjectId(empresa_id)})
            if not empresa:
                # print(f"Empresa no encontrada con ID: {empresa_id}")
                return [], 0
            
            empresa_nombre = empresa['nombre']
            
            # Buscar alertas por empresa_nombre y activo=True
            query = {'empresa_nombre': empresa_nombre, 'activo': True}
            alerts_data = self.collection.find(query).sort('fecha_creacion', -1).skip(skip).limit(limit)
            alerts = [MqttAlert.from_dict(alert_data) for alert_data in alerts_data]
            total = self.collection.count_documents(query)
            return alerts, total
        except Exception as e:
            # print(f"Error obteniendo alertas activas por empresa y sede: {e}")
            return [], 0
