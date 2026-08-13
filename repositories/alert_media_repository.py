import gridfs
from bson import ObjectId

from core.database import Database


class AlertMediaRepository:
    """Almacenamiento de archivos multimedia de las conversaciones (GridFS).

    Guarda los bytes descargados de WhatsApp en el propio Mongo y los sirve luego
    por la API de RescueBack, evitando depender de las URLs efímeras de Graph.
    """

    def __init__(self):
        self.db = Database().get_database()
        # Colección dedicada: `alert_media.files` / `alert_media.chunks`.
        self.fs = gridfs.GridFS(self.db, collection='alert_media')

    def store(self, content: bytes, filename: str, content_type: str, metadata: dict = None) -> str:
        """Guarda los bytes y devuelve el id (string) del archivo en GridFS."""
        file_id = self.fs.put(
            content,
            filename=filename,
            contentType=content_type,
            metadata=metadata or {},
        )
        return str(file_id)

    def get(self, file_id: str):
        """Devuelve el GridOut (stream + metadata) del archivo, o None si no existe."""
        try:
            return self.fs.get(ObjectId(file_id))
        except Exception:
            return None
