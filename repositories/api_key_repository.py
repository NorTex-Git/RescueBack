from bson import ObjectId
from datetime import datetime
from core.database import Database
from models.api_key import ApiKey


class ApiKeyRepository:
    def __init__(self):
        self.db = Database().get_database()
        self.collection = self.db.api_keys
        # Crear indices necesarios
        self._create_indexes()

    def _create_indexes(self):
        """Crea los indices necesarios para la coleccion"""
        try:
            # Indice unico para el prefijo: es la via de busqueda en cada request
            self.collection.create_index([("key_prefix", 1)], unique=True)
            # Indice para listar las llaves de una empresa
            self.collection.create_index([("empresa_id", 1)])
            # Indice para llaves vigentes
            self.collection.create_index([("activa", 1)])
        except Exception as e:
            # print(f"Error creando indices: {e}")
            pass

    def create(self, api_key):
        """Crea una nueva llave de API en la base de datos"""
        try:
            api_key.normalize_data()
            api_key_dict = api_key.to_dict()
            result = self.collection.insert_one(api_key_dict)
            api_key._id = result.inserted_id
            return api_key
        except Exception as e:
            if "duplicate key error" in str(e).lower() or "11000" in str(e):
                raise Exception("Colision de prefijo al generar la llave, reintente")
            raise Exception(f"Error creando llave de API: {str(e)}")

    def find_by_prefix(self, key_prefix):
        """Busca una llave por su prefijo publico. Incluye revocadas."""
        try:
            api_key_data = self.collection.find_one({"key_prefix": key_prefix})
            if api_key_data:
                return ApiKey.from_dict(api_key_data)
            return None
        except Exception as e:
            raise Exception(f"Error buscando llave de API: {str(e)}")

    def find_by_id(self, api_key_id):
        """Busca una llave por ID"""
        try:
            if isinstance(api_key_id, str):
                api_key_id = ObjectId(api_key_id)

            api_key_data = self.collection.find_one({"_id": api_key_id})
            if api_key_data:
                return ApiKey.from_dict(api_key_data)
            return None
        except Exception as e:
            raise Exception(f"Error buscando llave de API: {str(e)}")

    def find_by_empresa(self, empresa_id, incluir_revocadas=False):
        """Lista las llaves de una empresa"""
        try:
            if isinstance(empresa_id, str):
                empresa_id = ObjectId(empresa_id)

            query = {"empresa_id": empresa_id}
            if not incluir_revocadas:
                query["activa"] = True

            cursor = self.collection.find(query).sort("fecha_creacion", -1)
            return [ApiKey.from_dict(data) for data in cursor]
        except Exception as e:
            raise Exception(f"Error listando llaves de API: {str(e)}")

    def revoke(self, api_key_id):
        """Revoca una llave (soft delete). La llave nunca se borra: se conserva
        para auditoria de que credencial hizo que llamada."""
        try:
            if isinstance(api_key_id, str):
                api_key_id = ObjectId(api_key_id)

            result = self.collection.update_one(
                {"_id": api_key_id},
                {"$set": {"activa": False, "fecha_actualizacion": datetime.utcnow()}}
            )
            return result.matched_count > 0
        except Exception as e:
            raise Exception(f"Error revocando llave de API: {str(e)}")

    def touch_last_used(self, api_key_id):
        """Registra el ultimo uso de la llave. Best-effort: un fallo aqui no
        debe tumbar la peticion que ya fue autenticada."""
        try:
            if isinstance(api_key_id, str):
                api_key_id = ObjectId(api_key_id)

            self.collection.update_one(
                {"_id": api_key_id},
                {"$set": {"last_used_at": datetime.utcnow()}}
            )
        except Exception:
            pass
