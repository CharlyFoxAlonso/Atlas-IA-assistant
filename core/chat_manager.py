"""
core/chat_manager.py
Gestor de sesiones de chat múltiples para Atlas v3.9.
Cada chat tiene su propio historial, motor y metadata.
Se persisten en memory/Atlas_Memory/chats/{chat_id}.json
"""
import os
import json
from datetime import datetime, timezone
from core.security import log_seguridad

CHATS_DIR = "memory/Atlas_Memory/chats"

_ACTIVO = None


def _asegurar_directorio():
    os.makedirs(CHATS_DIR, exist_ok=True)


def _ruta_chat(chat_id: str) -> str:
    return os.path.join(CHATS_DIR, f"{chat_id}.json")


def _timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def crear_chat(nombre: str = "Nuevo chat", motor: str = "atlas",
               modelo_local: str = None, modelo_nube: str = None) -> str:
    """
    Crea un nuevo chat vacío con el nombre dado.
    Retorna el chat_id generado.
    """
    _asegurar_directorio()
    chat_id = _timestamp_id()

    from core.config import MODELO_LOCAL, MODELO_NUBE_DEFAULT
    if modelo_local is None:
        modelo_local = MODELO_LOCAL
    if modelo_nube is None:
        modelo_nube = MODELO_NUBE_DEFAULT

    chat = {
        "id": chat_id,
        "nombre": nombre,
        "creado": datetime.now().isoformat(),
        "motor": motor,
        "modelo_local": modelo_local,
        "modelo_nube": modelo_nube,
        "voz_activa": False,
        "agente_actual": "general",
        "messages": [],
        "historial_brain": [],
    }
    _guardar(chat_id, chat)
    log_seguridad("CHAT_CREADO", f"Chat '{nombre}' creado ({chat_id})")
    return chat_id


def _guardar(chat_id: str, datos: dict):
    _asegurar_directorio()
    ruta = _ruta_chat(chat_id)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


def _cargar(chat_id: str) -> dict:
    ruta = _ruta_chat(chat_id)
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def listar_chats() -> list:
    """
    Devuelve una lista de metadatos de todos los chats,
    ordenados por fecha de creación descendente (más reciente primero).
    Incluye campo 'activo' (True solo para el chat actualmente seleccionado).
    """
    _asegurar_directorio()
    chats = []
    for nombre_archivo in os.listdir(CHATS_DIR):
        if not nombre_archivo.endswith(".json"):
            continue
        chat_id = nombre_archivo[:-5]
        datos = _cargar(chat_id)
        if datos is None:
            continue
        chats.append({
            "id": datos.get("id", chat_id),
            "nombre": datos.get("nombre", "Sin nombre"),
            "creado": datos.get("creado", ""),
            "motor": datos.get("motor", "atlas"),
            "modelo_local": datos.get("modelo_local", ""),
            "modelo_nube": datos.get("modelo_nube", ""),
            "voz_activa": datos.get("voz_activa", False),
            "agente_actual": datos.get("agente_actual", "general"),
            "activo": (chat_id == _ACTIVO),
            "total_mensajes": len(datos.get("messages", [])),
        })
    chats.sort(key=lambda c: c["creado"], reverse=True)
    return chats


def activar_chat(chat_id: str) -> dict:
    """
    Carga el chat especificado como activo.
    Retorna los datos completos del chat (para que la UI los use).
    """
    global _ACTIVO
    datos = _cargar(chat_id)
    if datos is None:
        return None
    _ACTIVO = chat_id
    return datos


def chat_activo_id() -> str:
    """Devuelve el ID del chat actualmente activo."""
    return _ACTIVO


def chat_activo_datos() -> dict:
    """Devuelve los datos completos del chat activo."""
    if _ACTIVO is None:
        return None
    return _cargar(_ACTIVO)


def agregar_mensaje(rol: str, contenido: str, chat_id: str = None):
    """
    Agrega un mensaje al chat especificado (o al activo por defecto)
    y persiste el cambio inmediatamente.
    """
    cid = chat_id or _ACTIVO
    if cid is None:
        return
    datos = _cargar(cid)
    if datos is None:
        return
    datos.setdefault("messages", []).append({"role": rol, "content": contenido})

    if rol == "user" and datos.get("nombre") == "Nuevo chat":
        palabras = contenido.strip().split()
        preview = " ".join(palabras[:3])
        if len(preview) > 35:
            preview = preview[:32] + "..."
        datos["nombre"] = preview

    _guardar(cid, datos)


def guardar_chat(chat_id: str = None):
    """
    Persiste el estado actual del chat activo.
    Útil antes de cambiar de chat para no perder mensajes.
    """
    cid = chat_id or _ACTIVO
    if cid is None:
        return
    datos = _cargar(cid)
    if datos is None:
        return
    _guardar(cid, datos)


def renombrar_chat(chat_id: str, nuevo_nombre: str) -> bool:
    """Cambia el nombre de un chat."""
    datos = _cargar(chat_id)
    if datos is None:
        return False
    datos["nombre"] = nuevo_nombre
    _guardar(chat_id, datos)
    log_seguridad("CHAT_RENOMBRADO", f"Chat {chat_id} renombrado a '{nuevo_nombre}'")
    return True


def eliminar_chat(chat_id: str) -> bool:
    """Elimina un chat y su archivo JSON."""
    global _ACTIVO
    ruta = _ruta_chat(chat_id)
    if not os.path.exists(ruta):
        return False
    os.remove(ruta)
    log_seguridad("CHAT_ELIMINADO", f"Chat {chat_id} eliminado")
    if _ACTIVO == chat_id:
        _ACTIVO = None
    return True


def obtener_historial_brain(chat_id: str = None) -> list:
    """Obtiene el historial de brain.py para el chat especificado."""
    cid = chat_id or _ACTIVO
    if cid is None:
        return []
    datos = _cargar(cid)
    if datos is None:
        return []
    return datos.get("historial_brain", [])


def guardar_historial_brain(historial: list, chat_id: str = None):
    """Persiste el historial de brain.py en el chat especificado."""
    cid = chat_id or _ACTIVO
    if cid is None:
        return
    datos = _cargar(cid)
    if datos is None:
        return
    datos["historial_brain"] = historial
    _guardar(cid, datos)