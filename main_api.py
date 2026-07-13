import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

# Importar módulos de Atlas
from core.brain import pensar_con_streaming, HISTORIAL, set_historial, get_historial
from core.chat_manager import listar_chats, crear_chat, activar_chat, eliminar_chat, agregar_mensaje, guardar_chat
from core.vision import analizar_pantalla
from core.memory_manager import procesar_historial_para_memoria
from core.config import MODELO_LOCAL, MODELO_NUBE_DEFAULT, MODELO_GROQ_DEFAULT

app = FastAPI(title="Atlas API v4", description="API para acceso remoto a Atlas")

# --- Modelos de Datos ---
class ChatRequest(BaseModel):
    prompt: str
    chat_id: Optional[str] = None
    motor: Optional[str] = "atlas"
    modelo: Optional[str] = None

class ChatCreateRequest(BaseModel):
    nombre: str = "Nuevo chat API"

# --- Endpoints ---

@app.get("/")
async def root():
    return {"status": "online", "version": "v4", "name": "Atlas API"}

@app.get("/chats")
async def get_chats():
    """Lista todos los chats disponibles."""
    return listar_chats()

@app.post("/chats")
async def create_chat(req: ChatCreateRequest):
    """Crea un nuevo chat."""
    chat_id = crear_chat(req.nombre)
    return {"chat_id": chat_id, "nombre": req.nombre}

@app.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str):
    """Elimina un chat."""
    if eliminar_chat(chat_id):
        return {"status": "deleted", "chat_id": chat_id}
    raise HTTPException(status_code=404, detail="Chat no encontrado")

@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Envía un prompt a Atlas y recibe una respuesta en streaming.
    """
    # 1. Asegurar que haya un chat activo
    cid = req.chat_id
    if not cid:
        # Si no hay chat_id, crear uno temporal o usar el primero existente
        chats = listar_chats()
        if chats:
            cid = chats[0]["id"]
        else:
            cid = crear_chat("API Session")
    
    # 2. Activar el chat y cargar historial en brain.py
    datos = activar_chat(cid)
    if not datos:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    # Sincronizar historial de brain.py con el chat activo
    hb = get_historial() # Esto es un placeholder, usar obtener_historial_brain
    # Pero para simplicidad en la API, usaremos el chat_manager
    from core.chat_manager import obtener_historial_brain
    set_historial(obtener_historial_brain(cid))

    # 3. Agregar el mensaje del usuario
    agregar_mensaje("user", req.prompt, chat_id=cid)

    # 4. Configurar modelos
    motor = req.motor or "atlas"
    modelo_local = req.modelo if motor == "atlas" else None
    modelo_nube = req.modelo if motor == "prometeo" else MODELO_NUBE_DEFAULT
    modelo_groq = req.modelo if motor == "groq" else MODELO_GROQ_DEFAULT

    async def event_generator():
        try:
            # Usar el motor de streaming de Atlas
            for p, r in pensar_con_streaming(
                req.prompt,
                motor=motor,
                modelo_nube=modelo_nube,
                modelo_local=modelo_local,
                modelo_groq=modelo_groq
            ):
                if r:
                    yield r
            
            # Guardar la respuesta final en el chat (este es un desafío con streaming)
            # En una implementación real, deberíamos acumular 'r' y luego guardar.
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(event_generator(), media_type="text/plain")

@app.post("/memory/process")
async def process_memory():
    """Procesa el historial actual para extraer recuerdos."""
    # Para la API, procesamos el historial del chat activo o global
    guardados, errores = procesar_historial_para_memoria(HISTORIAL)
    return {"guardados": guardados, "errores": errores}

@app.get("/vision/capture")
async def capture_screen():
    """Captura la pantalla y devuelve el texto extraído."""
    ruta, texto = analizar_pantalla()
    if not texto:
        raise HTTPException(status_code=500, detail="No se pudo extraer texto de la pantalla")
    return {"texto": texto, "ruta_imagen": ruta}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
