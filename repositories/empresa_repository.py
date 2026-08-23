from bson import ObjectId
from datetime import datetime
import re
from core.database import Database
from models.empresa import Empresa

class EmpresaRepository:
    def __init__(self):
        self.db = Database().get_database()
        self.collection = self.db.empresas
        # Crear índices necesarios
        self._create_indexes()
    
    @staticmethod
    def _duplicate_error_message(error):
        details = getattr(error, 'details', None) or {}
        key_pattern = details.get('keyPattern') or {}
        if 'username' in key_pattern:
            return "El nombre de usuario ya está en uso"
        if 'email' in key_pattern:
            return "El correo ya está en uso"
        if 'nombre' in key_pattern:
            return "Ya existe una empresa con ese nombre"

        message = str(error).lower()
        if 'username_1' in message:
            return "El nombre de usuario ya está en uso"
        if 'email_1' in message:
            return "El correo ya está en uso"
        return "Ya existe una empresa con ese nombre"

    def _create_indexes(self):
        """Crea los índices necesarios para la colección"""
        try:
            # Índice único para el nombre (case-insensitive)
            self.collection.create_index(
                [("nombre", 1)],
                unique=True,
                collation={'locale': 'es', 'strength': 2}
            )
            # Índice único para username
            self.collection.create_index([("username", 1)], unique=True)
            # Índice único para email
            self.collection.create_index([("email", 1)], unique=True)
            # Índice para búsquedas por creado_por
            self.collection.create_index([("creado_por", 1)])
            # Índice para búsquedas por fecha_creacion
            self.collection.create_index([("fecha_creacion", -1)])
            # Índice para empresas activas
            self.collection.create_index([("activa", 1)])
        except Exception as e:
            # print(f"Error creando índices: {e}")
            pass
    
    def create(self, empresa):
        """Crea una nueva empresa en la base de datos"""
        try:
            empresa.normalize_data()
            empresa_dict = empresa.to_dict()
            result = self.collection.insert_one(empresa_dict)
            empresa._id = result.inserted_id
            return empresa
        except Exception as e:
            # Verificar si es error de duplicado
            if "duplicate key error" in str(e).lower() or "11000" in str(e):
                raise Exception(self._duplicate_error_message(e))
            raise Exception(f"Error creando empresa: {str(e)}")
    
    def find_by_id(self, empresa_id):
        """Busca una empresa por ID (solo activas)"""
        try:
            if isinstance(empresa_id, str):
                empresa_id = ObjectId(empresa_id)
            
            empresa_data = self.collection.find_one({"_id": empresa_id, "activa": True})
            if empresa_data:
                return Empresa.from_dict(empresa_data)
            return None
        except Exception as e:
            raise Exception(f"Error buscando empresa por ID: {str(e)}")
    
    def find_by_id_including_inactive(self, empresa_id):
        """Busca una empresa por ID incluyendo inactivas"""
        try:
            if isinstance(empresa_id, str):
                empresa_id = ObjectId(empresa_id)
            
            empresa_data = self.collection.find_one({"_id": empresa_id})
            if empresa_data:
                return Empresa.from_dict(empresa_data)
            return None
        except Exception as e:
            raise Exception(f"Error buscando empresa por ID (incluyendo inactivas): {str(e)}")
    
    def find_all(self, include_inactive=False):
        """Obtiene todas las empresas activas"""
        try:
            filter_query = {} if include_inactive else {"activa": True}
            empresas_data = self.collection.find(filter_query).sort("fecha_creacion", -1)
            empresas = []
            for empresa_data in empresas_data:
                empresas.append(Empresa.from_dict(empresa_data))
            return empresas
        except Exception as e:
            raise Exception(f"Error obteniendo empresas: {str(e)}")
    
    def find_by_nombre(self, nombre):
        """Busca una empresa por nombre (case-insensitive)"""
        try:
            normalized_name = (nombre or '').strip()
            empresa_data = self.collection.find_one(
                {"nombre": {"$regex": f"^{re.escape(normalized_name)}$", "$options": "i"}}
            )
            if empresa_data:
                return Empresa.from_dict(empresa_data)
            return None
        except Exception as e:
            raise Exception(f"Error buscando empresa por nombre: {str(e)}")
    
    def find_by_nombre_excluding_id(self, nombre, exclude_id):
        """Busca una empresa por nombre excluyendo un ID específico (para actualizaciones)"""
        try:
            if isinstance(exclude_id, str):
                exclude_id = ObjectId(exclude_id)
                
            empresa_data = self.collection.find_one({
                "nombre": {"$regex": f"^{re.escape((nombre or '').strip())}$", "$options": "i"},
                "_id": {"$ne": exclude_id}
            })
            if empresa_data:
                return Empresa.from_dict(empresa_data)
            return None
        except Exception as e:
            raise Exception(f"Error buscando empresa por nombre (excluyendo ID): {str(e)}")

    def find_by_username(self, username):
        """Busca una empresa por username"""
        try:
            data = self.collection.find_one({"username": username})
            return Empresa.from_dict(data) if data else None
        except Exception as e:
            raise Exception(f"Error buscando empresa por username: {str(e)}")
    
    def find_by_username_excluding_id(self, username, exclude_id):
        """Busca una empresa por username excluyendo un ID específico (para actualizaciones)"""
        try:
            if isinstance(exclude_id, str):
                exclude_id = ObjectId(exclude_id)
                
            data = self.collection.find_one({
                "username": username,
                "_id": {"$ne": exclude_id}
            })
            return Empresa.from_dict(data) if data else None
        except Exception as e:
            raise Exception(f"Error buscando empresa por username (excluyendo ID): {str(e)}")

    def find_by_email(self, email):
        """Busca una empresa por email"""
        try:
            data = self.collection.find_one({"email": email})
            return Empresa.from_dict(data) if data else None
        except Exception as e:
            raise Exception(f"Error buscando empresa por email: {str(e)}")
    
    def find_by_email_excluding_id(self, email, exclude_id):
        """Busca una empresa por email excluyendo un ID específico (para actualizaciones)"""
        try:
            if isinstance(exclude_id, str):
                exclude_id = ObjectId(exclude_id)
                
            data = self.collection.find_one({
                "email": email,
                "_id": {"$ne": exclude_id}
            })
            return Empresa.from_dict(data) if data else None
        except Exception as e:
            raise Exception(f"Error buscando empresa por email (excluyendo ID): {str(e)}")
    
    def find_by_creador(self, creado_por):
        """Busca empresas creadas por un super admin específico"""
        try:
            if isinstance(creado_por, str):
                creado_por = ObjectId(creado_por)
            
            empresas_data = self.collection.find({
                "creado_por": creado_por, 
                "activa": True
            }).sort("fecha_creacion", -1)
            
            empresas = []
            for empresa_data in empresas_data:
                empresas.append(Empresa.from_dict(empresa_data))
            return empresas
        except Exception as e:
            raise Exception(f"Error buscando empresas por creador: {str(e)}")
    
    def update(self, empresa_id, empresa):
        """Actualiza una empresa existente"""
        try:
            if isinstance(empresa_id, str):
                empresa_id = ObjectId(empresa_id)
            
            empresa.normalize_data()
            empresa.update_timestamp()
            empresa_dict = empresa.to_dict()
            empresa_dict.pop('_id', None)  # Remover _id del dict para actualización
            
            # Remover filtro de activa para permitir actualizar empresas inactivas
            result = self.collection.update_one(
                {"_id": empresa_id},
                {"$set": empresa_dict}
            )
            
            if result.matched_count > 0:
                return self.find_by_id_including_inactive(empresa_id)
            return None
        except Exception as e:
            if "duplicate key error" in str(e).lower() or "11000" in str(e):
                raise Exception(self._duplicate_error_message(e))
            raise Exception(f"Error actualizando empresa: {str(e)}")
    
    def soft_delete(self, empresa_id):
        """Realiza un soft delete de una empresa"""
        try:
            if isinstance(empresa_id, str):
                empresa_id = ObjectId(empresa_id)
            
            # Remover filtro de activa para permitir eliminar cualquier empresa
            result = self.collection.update_one(
                {"_id": empresa_id},
                {
                    "$set": {
                        "activa": False,
                        "fecha_actualizacion": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error eliminando empresa: {str(e)}")
    
    def hard_delete(self, empresa_id):
        """Elimina permanentemente una empresa (usar con precaución)"""
        try:
            if isinstance(empresa_id, str):
                empresa_id = ObjectId(empresa_id)
            
            result = self.collection.delete_one({"_id": empresa_id})
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Error eliminando empresa permanentemente: {str(e)}")
    
    def count(self, include_inactive=False):
        """Cuenta el total de empresas"""
        try:
            filter_query = {} if include_inactive else {"activa": True}
            return self.collection.count_documents(filter_query)
        except Exception as e:
            raise Exception(f"Error contando empresas: {str(e)}")
    
    def search_by_ubicacion(self, ubicacion):
        """Busca empresas por ubicación (búsqueda parcial)"""
        try:
            empresas_data = self.collection.find({
                "ubicacion": {"$regex": ubicacion, "$options": "i"},
                "activa": True
            }).sort("fecha_creacion", -1)
            
            empresas = []
            for empresa_data in empresas_data:
                empresas.append(Empresa.from_dict(empresa_data))
            return empresas
        except Exception as e:
            raise Exception(f"Error buscando empresas por ubicación: {str(e)}")
