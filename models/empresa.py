from datetime import datetime
from bson import ObjectId

from utils.role_utils import sanitize_roles

class Empresa:
    def __init__(
        self,
        nombre=None,
        descripcion=None,
        ubicacion=None,
        creado_por=None,
        username=None,
        email=None,
        password_hash=None,
        sedes=None,
        roles=None,
        last_login=None,
        activa=True,
        tipo_empresa_id=None,
        _id=None,
    ):
        self._id = _id or ObjectId()
        self.nombre = nombre
        self.descripcion = descripcion
        self.ubicacion = ubicacion
        self.creado_por = creado_por
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.sedes = sedes or []
        self.roles = sanitize_roles(roles)
        self.last_login = last_login
        self.tipo_empresa_id = tipo_empresa_id
        self.fecha_creacion = datetime.utcnow()
        self.fecha_actualizacion = datetime.utcnow()
        self.activa = activa  # Campo adicional para soft delete
    
    def to_dict(self):
        """Convierte el objeto Empresa a diccionario para MongoDB"""
        empresa_dict = {
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'ubicacion': self.ubicacion,
            'creado_por': self.creado_por,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'sedes': self.sedes,
            'roles': self.roles,
            'last_login': self.last_login,
            'tipo_empresa_id': self.tipo_empresa_id,
            'fecha_creacion': self.fecha_creacion,
            'fecha_actualizacion': self.fecha_actualizacion,
            'activa': self.activa
        }
        if self._id:
            empresa_dict['_id'] = self._id
        return empresa_dict
    
    @classmethod
    def from_dict(cls, data):
        """Crea un objeto Empresa desde un diccionario de MongoDB"""
        empresa = cls()
        empresa._id = data.get('_id')
        empresa.nombre = data.get('nombre')
        empresa.descripcion = data.get('descripcion')
        empresa.ubicacion = data.get('ubicacion')
        empresa.creado_por = data.get('creado_por')
        empresa.username = data.get('username')
        empresa.email = data.get('email')
        empresa.password_hash = data.get('password_hash')
        empresa.sedes = data.get('sedes', [])
        empresa.roles = sanitize_roles(data.get('roles', []))
        empresa.last_login = data.get('last_login')
        empresa.tipo_empresa_id = data.get('tipo_empresa_id')
        empresa.fecha_creacion = data.get('fecha_creacion')
        empresa.fecha_actualizacion = data.get('fecha_actualizacion')
        empresa.activa = data.get('activa', True)
        return empresa
    
    def to_json(self):
        """Convierte a JSON serializable"""
        return {
            '_id': str(self._id) if self._id else None,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'ubicacion': self.ubicacion,
            'creado_por': str(self.creado_por) if self.creado_por else None,
            'username': self.username,
            'email': self.email,
            'sedes': self.sedes,
            'roles': self.roles,
            'last_login': self.last_login.isoformat() if isinstance(self.last_login, datetime) else self.last_login,
            'tipo_empresa_id': str(self.tipo_empresa_id) if self.tipo_empresa_id else None,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            'activa': self.activa
        }
    
    def validate(self):
        """Valida los datos de la empresa"""
        errors = []
        
        if not self.nombre or len(self.nombre.strip()) == 0:
            errors.append("El nombre de la empresa es obligatorio")
        
        if len(self.nombre.strip()) < 2:
            errors.append("El nombre debe tener al menos 2 caracteres")
        
        if len(self.nombre.strip()) > 100:
            errors.append("El nombre no puede exceder 100 caracteres")
        
        if not self.descripcion or len(self.descripcion.strip()) == 0:
            errors.append("La descripción de la empresa es obligatoria")
        
        if len(self.descripcion.strip()) < 10:
            errors.append("La descripción debe tener al menos 10 caracteres")
        
        if len(self.descripcion.strip()) > 500:
            errors.append("La descripción no puede exceder 500 caracteres")
        
        if not self.ubicacion or len(self.ubicacion.strip()) == 0:
            errors.append("La ubicación de la empresa es obligatoria")
        
        if len(self.ubicacion.strip()) < 3:
            errors.append("La ubicación debe tener al menos 3 caracteres")
        
        if len(self.ubicacion.strip()) > 200:
            errors.append("La ubicación no puede exceder 200 caracteres")
        
        if not self.creado_por:
            errors.append("El ID del super admin creador es obligatorio")

        if not self.username or len(self.username.strip()) == 0:
            errors.append("El nombre de usuario es obligatorio")

        if not self.email or len(self.email.strip()) == 0:
            errors.append("El correo es obligatorio")
        elif "@" not in self.email:
            errors.append("El correo debe ser válido")

        if not self.password_hash:
            errors.append("La contraseña es obligatoria")

        if self.sedes is not None:
            if not isinstance(self.sedes, list):
                errors.append("Las sedes deben ser una lista")
            else:
                for sede in self.sedes:
                    if not isinstance(sede, str) or len(sede.strip()) == 0:
                        errors.append("Cada sede debe ser una cadena no vacía")
                        break

        if self.roles is not None:
            if not isinstance(self.roles, list):
                errors.append("Los roles deben ser una lista")
            else:
                for rol in self.roles:
                    if not isinstance(rol, dict):
                        errors.append("Cada rol debe ser un objeto con nombre, is_creator e is_alert_manager")
                        break
                    nombre = rol.get('nombre')
                    if not nombre or not isinstance(nombre, str) or len(nombre.strip()) == 0:
                        errors.append("Cada rol debe tener un nombre válido")
                        break
                    if not isinstance(rol.get('is_creator', False), bool):
                        errors.append("El campo is_creator de cada rol debe ser booleano")
                        break
                    if not isinstance(rol.get('is_alert_manager', False), bool):
                        errors.append("El campo is_alert_manager de cada rol debe ser booleano")
                        break

        return errors
    
    def update_timestamp(self):
        """Actualiza el timestamp de modificación"""
        self.fecha_actualizacion = datetime.utcnow()
    
    def normalize_data(self):
        """Normaliza los datos antes de guardar"""
        if self.nombre:
            self.nombre = self.nombre.strip()
        if self.descripcion:
            self.descripcion = self.descripcion.strip()
        if self.ubicacion:
            self.ubicacion = self.ubicacion.strip()
        if self.username:
            self.username = self.username.strip()
        if self.email:
            self.email = self.email.strip()
        if self.sedes and isinstance(self.sedes, list):
            self.sedes = [sede.strip() for sede in self.sedes if isinstance(sede, str)]
        self.roles = sanitize_roles(self.roles)
