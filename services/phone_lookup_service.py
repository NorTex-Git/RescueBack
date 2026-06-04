from repositories.usuario_repository import UsuarioRepository
from repositories.empresa_repository import EmpresaRepository
from typing import Dict, Any, Optional


class PhoneLookupService:
    """
    Servicio para buscar información de una persona por su número de teléfono.
    No requiere autenticación.
    """
    
    def __init__(self):
        self.usuario_repository = UsuarioRepository()
        self.empresa_repository = EmpresaRepository()
    
    def lookup_by_phone(self, telefono: str) -> Dict[str, Any]:
        """
        Busca información de una persona por su número de teléfono.
        
        Args:
            telefono: Número de teléfono a buscar
            
        Returns:
            Dict con la información encontrada o error si no se encuentra
        """
        try:
            # Validar que el teléfono no esté vacío
            if not telefono or not telefono.strip():
                return {
                    'success': False,
                    'error': 'Teléfono requerido',
                    'message': 'El número de teléfono es obligatorio'
                }
            
            # Normalizar el teléfono
            telefono_normalizado = telefono.strip()
            
            # Buscar usuario por teléfono
            usuario = self.usuario_repository.find_by_telefono_global(telefono_normalizado)
            
            if not usuario:
                return {
                    'success': False,
                    'error': 'Usuario no encontrado',
                    'message': f'No se encontró ningún usuario con el teléfono {telefono_normalizado}'
                }
            
            # Obtener información de la empresa
            empresa = self.empresa_repository.find_by_id(usuario.empresa_id)
            
            if not empresa:
                return {
                    'success': False,
                    'error': 'Empresa no encontrada',
                    'message': 'La empresa asociada al usuario no fue encontrada'
                }
            
            # Determinar detalles del rol, buscando en la empresa
            rol_detalle = next(
                (
                    {
                        'nombre': entry.get('nombre'),
                        'is_creator': bool(entry.get('is_creator', False)),
                        'is_alert_manager': bool(entry.get('is_alert_manager', False))
                    }
                    for entry in (empresa.roles or [])
                    if isinstance(entry, dict)
                    and (entry.get('nombre') or '').strip().lower() == (usuario.rol or '').strip().lower()
                ),
                None
            )

            # Construir respuesta con la información solicitada
            return {
                'success': True,
                'data': {
                    'id': str(usuario._id),
                    'nombre': usuario.nombre,
                    'empresa_id': str(empresa._id) if getattr(empresa, '_id', None) else None,
                    'empresa': empresa.nombre,
                    'sede': usuario.sede,
                    'telefono': usuario.telefono,
                    'cedula': usuario.cedula,
                    'rol': rol_detalle or usuario.rol,
                    'email': usuario.email
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': 'Error interno',
                'message': f'Error al buscar información: {str(e)}'
            }
