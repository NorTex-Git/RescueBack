"""Utilidades para normalizar y validar roles de empresas."""

from typing import Iterable, List, Optional

# Roles predeterminados para nuevas empresas
DEFAULT_EMPRESA_ROLES = [
    {'nombre': 'operador', 'is_creator': False, 'is_alert_manager': False},
    {'nombre': 'supervisor', 'is_creator': False, 'is_alert_manager': False},
]


def _extract_role_name(role_entry) -> Optional[str]:
    """Obtiene el nombre del rol desde distintas representaciones."""
    if isinstance(role_entry, dict):
        return role_entry.get('nombre') or role_entry.get('name') or role_entry.get('role')
    if isinstance(role_entry, str):
        return role_entry
    return None


def _extract_role_flag(role_entry) -> bool:
    """Obtiene el indicador is_creator de manera segura."""
    if isinstance(role_entry, dict):
        return bool(role_entry.get('is_creator', False))
    return False


def _extract_role_manager_flag(role_entry) -> bool:
    """Obtiene el indicador is_alert_manager de manera segura."""
    if isinstance(role_entry, dict):
        return bool(role_entry.get('is_alert_manager', False))
    return False


def normalize_role_name(name: Optional[str]) -> Optional[str]:
    """Normaliza el nombre del rol (strip y minúsculas)."""
    if not isinstance(name, str):
        return None
    normalized = name.strip().lower()
    return normalized or None


def sanitize_roles(raw_roles: Optional[Iterable]) -> List[dict]:
    """Limpia y normaliza una colección de roles.

    Acepta listas de strings o diccionarios y devuelve siempre una lista de
    diccionarios con las claves `nombre` y `is_creator`.
    """

    if not raw_roles:
        return [role.copy() for role in DEFAULT_EMPRESA_ROLES]

    if isinstance(raw_roles, (str, dict)):
        roles_iterable = [raw_roles]
    else:
        roles_iterable = list(raw_roles)

    cleaned: List[dict] = []
    seen = set()

    for entry in roles_iterable:
        raw_name = _extract_role_name(entry)
        normalized_name = normalize_role_name(raw_name)
        if not normalized_name or normalized_name in seen:
            continue
        seen.add(normalized_name)

        is_creator_flag = _extract_role_flag(entry)
        is_alert_manager_flag = _extract_role_manager_flag(entry)
        cleaned.append({
            'nombre': normalized_name,
            'is_creator': bool(is_creator_flag),
            'is_alert_manager': bool(is_alert_manager_flag)
        })

    if not cleaned:
        return [role.copy() for role in DEFAULT_EMPRESA_ROLES]

    return cleaned


def company_role_names(roles: Iterable) -> List[str]:
    """Devuelve los nombres normalizados de los roles suministrados."""
    sanitized = sanitize_roles(roles)
    return [role['nombre'] for role in sanitized]


def is_role_allowed(role: str, roles_pool: Iterable) -> bool:
    """Verifica si un rol pertenece al listado proporcionado."""
    normalized = normalize_role_name(role)
    if not normalized:
        return False
    allowed = {entry['nombre'] for entry in sanitize_roles(roles_pool)}
    return normalized in allowed
