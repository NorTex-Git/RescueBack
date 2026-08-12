from bson import ObjectId
from datetime import datetime
from core.database import Database
from models.hardware import Hardware

class HardwareRepository:
    def __init__(self):
        self.db = Database().get_database()
        self.collection = self.db.hardware
        self._create_indexes()

    def _create_indexes(self):
        try:
            self.collection.create_index([('nombre', 1)], unique=True)
            self.collection.create_index([('empresa_id', 1)])
            self.collection.create_index([('activa', 1)])
        except Exception as exc:
            # print(f'Error creando indices de hardware: {exc}')
            pass

    def create(self, hardware: Hardware):
        try:
            hw_dict = hardware.to_dict()
            result = self.collection.insert_one(hw_dict)
            hardware._id = result.inserted_id
            return hardware
        except Exception as exc:
            raise Exception(f'Error creando hardware: {str(exc)}')

    def find_by_id(self, hardware_id):
        try:
            if isinstance(hardware_id, str):
                hardware_id = ObjectId(hardware_id)
            data = self.collection.find_one({'_id': hardware_id, 'activa': True})
            return Hardware.from_dict(data) if data else None
        except Exception as exc:
            raise Exception(f'Error buscando hardware por ID: {str(exc)}')

    def find_by_id_including_inactive(self, hardware_id):
        """Find hardware by ID including inactive ones"""
        try:
            if isinstance(hardware_id, str):
                hardware_id = ObjectId(hardware_id)
            data = self.collection.find_one({'_id': hardware_id})
            return Hardware.from_dict(data) if data else None
        except Exception as exc:
            raise Exception(f'Error buscando hardware por ID (incluyendo inactivos): {str(exc)}')

    def find_by_nombre(self, nombre):
        try:
            data = self.collection.find_one({'nombre': nombre, 'activa': True})
            return Hardware.from_dict(data) if data else None
        except Exception as exc:
            raise Exception(f'Error buscando hardware por nombre: {str(exc)}')

    def find_by_nombre_excluding_id(self, nombre, exclude_id):
        """Busca hardware por nombre excluyendo un ID específico"""
        try:
            if isinstance(exclude_id, str):
                exclude_id = ObjectId(exclude_id)
            data = self.collection.find_one({
                'nombre': nombre, 
                'activa': True,
                '_id': {'$ne': exclude_id}
            })
            return Hardware.from_dict(data) if data else None
        except Exception as exc:
            raise Exception(f'Error buscando hardware por nombre (excluyendo ID): {str(exc)}')

    def find_all(self):
        try:
            cursor = self.collection.find({'activa': True}).sort('fecha_creacion', -1)
            return [Hardware.from_dict(d) for d in cursor]
        except Exception as exc:
            raise Exception(f'Error obteniendo hardware: {str(exc)}')

    def find_by_empresa(self, empresa_id):
        try:
            if isinstance(empresa_id, str):
                empresa_id = ObjectId(empresa_id)
            cursor = self.collection.find({'empresa_id': empresa_id, 'activa': True}).sort('fecha_creacion', -1)
            return [Hardware.from_dict(d) for d in cursor]
        except Exception as exc:
            raise Exception(f'Error obteniendo hardware por empresa: {str(exc)}')
    
    def find_with_filters(self, filters=None):
        """Find hardware with optional filters"""
        try:
            query = {'activa': True}
            
            if filters:
                # Filter by type
                if filters.get('tipo'):
                    query['tipo'] = filters['tipo']
                
                # Filter by empresa
                if filters.get('empresa_id'):
                    empresa_id = filters['empresa_id']
                    if isinstance(empresa_id, str):
                        empresa_id = ObjectId(empresa_id)
                    query['empresa_id'] = empresa_id
                
                # Filter by sede
                if filters.get('sede'):
                    query['sede'] = filters['sede']
                
                # Search in name (case insensitive)
                if filters.get('search'):
                    search_term = filters['search']
                    query['$or'] = [
                        {'nombre': {'$regex': search_term, '$options': 'i'}},
                        {'tipo': {'$regex': search_term, '$options': 'i'}},
                        {'sede': {'$regex': search_term, '$options': 'i'}},
                        {'datos.brand': {'$regex': search_term, '$options': 'i'}},
                        {'datos.model': {'$regex': search_term, '$options': 'i'}},
                        {'datos.datos.brand': {'$regex': search_term, '$options': 'i'}},
                        {'datos.datos.model': {'$regex': search_term, '$options': 'i'}}
                    ]
                
                # Filter by status (in nested datos)
                if filters.get('status'):
                    status = filters['status']
                    query['$or'] = [
                        {'datos.status': status},
                        {'datos.datos.status': status}
                    ]
                
                # Filter by stock level
                if filters.get('min_stock') is not None:
                    min_stock = filters['min_stock']
                    query['$or'] = [
                        {'datos.stock': {'$gte': min_stock}},
                        {'datos.datos.stock': {'$gte': min_stock}}
                    ]
            
            cursor = self.collection.find(query).sort('fecha_creacion', -1)
            return [Hardware.from_dict(d) for d in cursor]
        except Exception as exc:
            raise Exception(f'Error filtrando hardware: {str(exc)}')

    def find_all_including_inactive(self):
        """Find all hardware including inactive ones"""
        try:
            cursor = self.collection.find({}).sort('fecha_creacion', -1)
            return [Hardware.from_dict(d) for d in cursor]
        except Exception as exc:
            raise Exception(f'Error obteniendo todo el hardware: {str(exc)}')

    def find_by_empresa_including_inactive(self, empresa_id):
        """Find all hardware by empresa including inactive ones"""
        try:
            if isinstance(empresa_id, str):
                empresa_id = ObjectId(empresa_id)
            cursor = self.collection.find({'empresa_id': empresa_id}).sort('fecha_creacion', -1)
            return [Hardware.from_dict(d) for d in cursor]
        except Exception as exc:
            raise Exception(f'Error obteniendo hardware por empresa (incluyendo inactivos): {str(exc)}')

    def find_with_filters_including_inactive(self, filters=None):
        """Find hardware with optional filters including inactive ones"""
        try:
            query = {}
            
            if filters:
                # Filter by type
                if filters.get('tipo'):
                    query['tipo'] = filters['tipo']
                
                # Filter by empresa
                if filters.get('empresa_id'):
                    empresa_id = filters['empresa_id']
                    if isinstance(empresa_id, str):
                        empresa_id = ObjectId(empresa_id)
                    query['empresa_id'] = empresa_id
                
                # Filter by sede
                if filters.get('sede'):
                    query['sede'] = filters['sede']
                
                # Filter by active status
                if filters.get('activa') is not None:
                    query['activa'] = filters['activa']
                
                # Search in name (case insensitive)
                if filters.get('search'):
                    search_term = filters['search']
                    query['$or'] = [
                        {'nombre': {'$regex': search_term, '$options': 'i'}},
                        {'tipo': {'$regex': search_term, '$options': 'i'}},
                        {'sede': {'$regex': search_term, '$options': 'i'}},
                        {'datos.brand': {'$regex': search_term, '$options': 'i'}},
                        {'datos.model': {'$regex': search_term, '$options': 'i'}},
                        {'datos.datos.brand': {'$regex': search_term, '$options': 'i'}},
                        {'datos.datos.model': {'$regex': search_term, '$options': 'i'}}
                    ]
                
                # Filter by status (in nested datos)
                if filters.get('status'):
                    status = filters['status']
                    query['$or'] = [
                        {'datos.status': status},
                        {'datos.datos.status': status}
                    ]
                
                # Filter by stock level
                if filters.get('min_stock') is not None:
                    min_stock = filters['min_stock']
                    query['$or'] = [
                        {'datos.stock': {'$gte': min_stock}},
                        {'datos.datos.stock': {'$gte': min_stock}}
                    ]
            
            cursor = self.collection.find(query).sort('fecha_creacion', -1)
            return [Hardware.from_dict(d) for d in cursor]
        except Exception as exc:
            raise Exception(f'Error filtrando hardware (incluyendo inactivos): {str(exc)}')

    def find_by_topic_including_inactive(self, topic):
        """Find hardware by topic including inactive ones"""
        try:
            data = self.collection.find_one({'topic': topic})
            return Hardware.from_dict(data) if data else None
        except Exception as exc:
            raise Exception(f'Error buscando hardware por topic (incluyendo inactivos): {str(exc)}')

    def update_physical_status_by_topic(self, topic, physical_status):
        """Update physical_status by hardware topic"""
        try:
            update_data = {
                'physical_status': physical_status,
                'fecha_actualizacion': datetime.utcnow()
            }
            result = self.collection.update_one({'topic': topic}, {'$set': update_data})
            if result.matched_count > 0:
                return self.find_by_topic_including_inactive(topic)
            return None
        except Exception as exc:
            raise Exception(f'Error actualizando physical_status por topic: {str(exc)}')

    def update_physical_status_by_empresa_hardware(self, empresa_nombre, hardware_nombre, physical_status):
        """Update physical_status by empresa nombre and hardware nombre"""
        try:
            empresa = self.db.empresas.find_one({'nombre': empresa_nombre})
            if not empresa:
                return None

            update_data = {
                'physical_status': physical_status,
                'fecha_actualizacion': datetime.utcnow()
            }
            query = {
                'empresa_id': empresa.get('_id'),
                'nombre': hardware_nombre
            }
            previous = self.collection.find_one(query)
            result = self.collection.update_one(query, {'$set': update_data})
            if result.matched_count > 0:
                data = self.collection.find_one(query)
                if not data:
                    return None
                return Hardware.from_dict(data), (previous or {}).get('physical_status') or {}
            return None
        except Exception as exc:
            raise Exception(f'Error actualizando physical_status por empresa/hardware: {str(exc)}')

    def update_physical_status_by_id(self, hardware_id, physical_status):
        """Update physical_status by hardware ID"""
        try:
            if isinstance(hardware_id, str):
                hardware_id = ObjectId(hardware_id)
            update_data = {
                'physical_status': physical_status,
                'fecha_actualizacion': datetime.utcnow()
            }
            result = self.collection.update_one({'_id': hardware_id}, {'$set': update_data})
            if result.matched_count > 0:
                return self.find_by_id_including_inactive(hardware_id)
            return None
        except Exception as exc:
            raise Exception(f'Error actualizando physical_status por ID: {str(exc)}')

    def update(self, hardware_id, hardware: Hardware):
        try:
            if isinstance(hardware_id, str):
                hardware_id = ObjectId(hardware_id)
            hardware.update_timestamp()
            hw_dict = hardware.to_dict()
            hw_dict.pop('_id', None)
            # Remove activa filter from update query to allow updating inactive hardware
            result = self.collection.update_one({'_id': hardware_id}, {'$set': hw_dict})
            if result.matched_count > 0:
                return self.find_by_id_including_inactive(hardware_id)
            return None
        except Exception as exc:
            raise Exception(f'Error actualizando hardware: {str(exc)}')

    def soft_delete(self, hardware_id):
        try:
            if isinstance(hardware_id, str):
                hardware_id = ObjectId(hardware_id)
            # Remove activa filter to allow soft delete of any hardware
            result = self.collection.update_one({'_id': hardware_id}, {'$set': {'activa': False, 'fecha_actualizacion': datetime.utcnow()}})
            return result.modified_count > 0
        except Exception as exc:
            raise Exception(f'Error eliminando hardware: {str(exc)}')
