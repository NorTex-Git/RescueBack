from datetime import datetime
from bson import ObjectId

class MqttAlert:
    """Modelo para almacenar alertas recibidas por MQTT o creadas por usuarios"""
    
    def __init__(self, empresa_nombre=None, sede=None, data=None, 
                 tipo_alerta=None,
                 nombre_alerta=None,
                 descripcion=None,
                 prioridad=None,
                 image_alert=None,
                 elementos_necesarios=None,
                 instrucciones=None,
                 numeros_telefonicos=None, 
                 topic=None, 
                 topics_otros_hardware=None,
                 activacion_alerta=None,
                 ubicacion=None, 
                 fecha_desactivacion=None, 
                 activo=True, 
                 _id=None):
        self._id = _id or ObjectId()
        self.empresa_nombre = empresa_nombre
        self.sede = sede
        self.data = data or {}  # datos de la alerta
        
        # Campos de la alerta
        self.tipo_alerta = tipo_alerta
        self.nombre_alerta = nombre_alerta
        self.descripcion = descripcion
        self.prioridad = prioridad or 'media'
        self.image_alert = image_alert  # imagen de la alerta (base64 o URL)
        self.elementos_necesarios = elementos_necesarios or []  # implementos necesarios del tipo de alarma
        self.instrucciones = instrucciones or []  # recomendaciones del tipo de alarma
        
        # Campos específicos para hardware
        self.numeros_telefonicos = numeros_telefonicos or []  # números telefónicos de usuarios relacionados
        self.topic = topic  # topic del hardware
        self.topics_otros_hardware = topics_otros_hardware or []  # topics de otros hardware de la misma empresa y sede
        
        # Información de activación
        self.activacion_alerta = activacion_alerta or {}  # quien activó la alerta
        
        # Ubicación de la alerta
        self.ubicacion = ubicacion or {}  # información de ubicación
        
        # Campos comunes
        self.activo = activo  # estado activo/inactivo de la alerta
        self.fecha_creacion = datetime.utcnow()
        self.fecha_actualizacion = datetime.utcnow()
        self.fecha_desactivacion = fecha_desactivacion  # cuando se desactivó la alerta
        self.desactivado_por = {}  # información sobre quién/qué desactivó la alerta
        self.mensaje_desactivacion = None  # mensaje opcional de desactivación
        
    def to_dict(self):
        """Convierte el objeto a diccionario para MongoDB"""
        alert_dict = {
            'empresa_nombre': self.empresa_nombre,
            'sede': self.sede,
            'data': self.data,
            'tipo_alerta': self.tipo_alerta,
            'nombre_alerta': self.nombre_alerta,
            'descripcion': self.descripcion,
            'prioridad': self.prioridad,
            'image_alert': self.image_alert,
            'elementos_necesarios': self.elementos_necesarios,
            'instrucciones': self.instrucciones,
            'numeros_telefonicos': self.numeros_telefonicos,
            'topic': self.topic,
            'topics_otros_hardware': self.topics_otros_hardware,
            'activacion_alerta': self.activacion_alerta,
            'ubicacion': self.ubicacion,
            'activo': self.activo,
            'fecha_creacion': self.fecha_creacion,
            'fecha_actualizacion': self.fecha_actualizacion,
            'fecha_desactivacion': self.fecha_desactivacion,
            'desactivado_por': self.desactivado_por,
            'mensaje_desactivacion': self.mensaje_desactivacion
        }
        if self._id:
            alert_dict['_id'] = self._id
        return alert_dict
    
    @classmethod
    def from_dict(cls, data):
        """Crea un objeto MqttAlert desde un diccionario de MongoDB"""
        alert = cls()
        alert._id = data.get('_id')
        alert.empresa_nombre = data.get('empresa_nombre')
        alert.sede = data.get('sede')
        alert.data = data.get('data', {})
        alert.tipo_alerta = data.get('tipo_alerta')
        alert.nombre_alerta = data.get('nombre_alerta')
        alert.descripcion = data.get('descripcion')
        alert.prioridad = data.get('prioridad', 'media')
        alert.image_alert = data.get('image_alert')
        alert.elementos_necesarios = data.get('elementos_necesarios', [])
        alert.instrucciones = data.get('instrucciones', [])
        alert.numeros_telefonicos = data.get('numeros_telefonicos', [])
        alert.topic = data.get('topic')
        alert.topics_otros_hardware = data.get('topics_otros_hardware', [])
        alert.activacion_alerta = data.get('activacion_alerta', {})
        alert.ubicacion = data.get('ubicacion', {})
        alert.activo = data.get('activo', True)
        alert.fecha_creacion = data.get('fecha_creacion')
        alert.fecha_actualizacion = data.get('fecha_actualizacion')
        alert.fecha_desactivacion = data.get('fecha_desactivacion')
        alert.desactivado_por = data.get('desactivado_por', {})
        alert.mensaje_desactivacion = data.get('mensaje_desactivacion')
        return alert
    
    def to_json(self):
        """Convierte a JSON serializable"""
        from bson import ObjectId
        import json
        
        def convert_objectids(obj):
            """Convierte recursivamente ObjectIds a strings"""
            if isinstance(obj, ObjectId):
                return str(obj)
            elif isinstance(obj, dict):
                return {key: convert_objectids(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_objectids(item) for item in obj]
            elif hasattr(obj, 'isoformat'):  # datetime objects
                return obj.isoformat()
            else:
                return obj
        
        return {
            '_id': str(self._id) if self._id else None,
            'empresa_nombre': self.empresa_nombre,
            'sede': self.sede,
            'data': convert_objectids(self.data),
            'tipo_alerta': self.tipo_alerta,
            'nombre_alerta': self.nombre_alerta,
            'descripcion': self.descripcion,
            'prioridad': self.prioridad,
            'image_alert': self.image_alert,
            'elementos_necesarios': self.elementos_necesarios,
            'instrucciones': self.instrucciones,
            'numeros_telefonicos': self.numeros_telefonicos,
            'topic': self.topic,
            'topics_otros_hardware': self.topics_otros_hardware,
            'activacion_alerta': convert_objectids(self.activacion_alerta),
            'ubicacion': self.ubicacion,
            'activo': self.activo,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            'fecha_desactivacion': self.fecha_desactivacion.isoformat() if self.fecha_desactivacion else None,
            'desactivado_por': self.desactivado_por,
            'mensaje_desactivacion': self.mensaje_desactivacion
        }
    
    def deactivate(self, desactivado_por_id=None, desactivado_por_tipo=None, mensaje_desactivacion=None, desactivado_por_nombre=None):
        """Desactiva la alerta"""
        self.activo = False
        self.fecha_desactivacion = datetime.utcnow()

        # Agregar mensaje de desactivación si se proporciona
        if mensaje_desactivacion:
            self.mensaje_desactivacion = mensaje_desactivacion.strip()

        # Agregar información sobre quién desactivó. Se persiste el nombre para que
        # el frontend pueda mostrar "Desactivada por" sin resolver el id.
        if desactivado_por_id and desactivado_por_tipo:
            self.desactivado_por = {
                'id': desactivado_por_id,
                'tipo': desactivado_por_tipo,
                'nombre': desactivado_por_nombre or '',
                'fecha_desactivacion': self.fecha_desactivacion.isoformat()
            }

        self.update_timestamp()
    
    def activate(self):
        """Activa la alerta"""
        self.activo = True
        self.fecha_desactivacion = None
        self.update_timestamp()
    
    def toggle_status(self):
        """Alterna el estado activo/inactivo"""
        if self.activo:
            self.deactivate()
        else:
            self.activate()
    
    def update_timestamp(self):
        """Actualiza el timestamp de modificación"""
        self.fecha_actualizacion = datetime.utcnow()
    
    def validate(self):
        """Valida los datos de la alerta"""
        errors = []
        
        if not self.empresa_nombre or len(self.empresa_nombre.strip()) == 0:
            errors.append("El nombre de la empresa es obligatorio")
        
        if not self.sede or len(self.sede.strip()) == 0:
            errors.append("La sede es obligatoria")
        
        return errors
    
    def normalize_data(self):
        """Normaliza los datos antes de guardar"""
        if self.empresa_nombre:
            self.empresa_nombre = self.empresa_nombre.strip()
        if self.sede:
            self.sede = self.sede.strip()
    
    @classmethod
    def create_from_hardware(cls, empresa_nombre, sede, hardware_nombre, hardware_id, 
                           tipo_alerta=None, data=None, **kwargs):
        """Crea una alerta desde hardware MQTT"""
        activacion_alerta = {
            'tipo_activacion': 'hardware',
            'nombre': hardware_nombre,
            'id': hardware_id
        }
        
        return cls(
            empresa_nombre=empresa_nombre,
            sede=sede,
            tipo_alerta=tipo_alerta,
            data=data,
            activacion_alerta=activacion_alerta,
            **kwargs
        )
    
    @classmethod
    def create_from_user(cls, empresa_nombre, sede, usuario_id, usuario_nombre, tipo_alerta, 
                        descripcion, prioridad='media', data=None, **kwargs):
        """Crea una alerta desde usuario o empresa"""
        
        # Detectar tipo de activación basado en los datos proporcionados
        # Si data contiene creador_tipo, usarlo; sino, detectar por el nombre
        tipo_activacion = 'usuario'  # Por defecto
        
        if data and isinstance(data, dict):
            creador_tipo = data.get('creador_tipo')
            if creador_tipo == 'empresa':
                tipo_activacion = 'empresa'
            elif usuario_nombre and usuario_nombre.startswith('Empresa '):
                tipo_activacion = 'empresa'
        
        activacion_alerta = {
            'tipo_activacion': tipo_activacion,
            'nombre': usuario_nombre,
            'id': usuario_id
        }
        
        return cls(
            empresa_nombre=empresa_nombre,
            sede=sede,
            tipo_alerta=tipo_alerta,
            descripcion=descripcion,
            prioridad=prioridad,
            data=data,
            activacion_alerta=activacion_alerta,
            **kwargs
        )
