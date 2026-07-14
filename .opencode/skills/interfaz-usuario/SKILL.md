---
name: interfaz-usuario
# domain: modifica interfaces de usuario (Streamlit, CLI, API, entry points)
type: domain
description: |
  Interfaces de Atlas: aplicación Streamlit, CLI interactivo, API REST y entry points.
  Usar al modificar la experiencia de usuario, controles, comandos, endpoints
  o presentación de respuestas. No usar para modificar la lógica del núcleo,
  RAG o configuración del sistema.
---

# Interfaz de Usuario

## Propósito

Modificar, depurar o extender las interfaces de usuario de Atlas, incluyendo la UI web (Streamlit), el CLI interactivo, la API REST (FastAPI) y los entry points (`run.py`, `run.bat`, `run_ui.bat`).

## Cuándo usarla

- El usuario menciona la interfaz, UI, Streamlit, API, endpoint, comando, entrada de chat, botón, menú
- El usuario pide agregar, modificar o eliminar funcionalidad visible en la UI web o CLI
- El usuario reporta errores en la interfaz (no en la lógica interna)
- El usuario solicita nuevos comandos `!` en el chat
- El usuario pide cambios en el Streamlit sidebar, métricas, selectores o paneles

## Cuándo no usarla

- La lógica de generación de respuestas o enrutamiento → `nucleo-atlas`
- El pipeline de RAG o ingesta → `base-conocimiento`
- La instalación o configuración del entorno → `configuracion-sistema`

## Workflow

1. **Identificar la interfaz** — CLI (`atlas_chat.py`), Web (`atlas_ui.py`), API (`main_api.py`) o entry point (`run.py`)
2. **Leer el flujo existente** — Para la UI web, entender `_ensure_state()`, el renderizado de sidebar y el bucle de chat. Para la API, entender los endpoints y modelos de datos
3. **Modificar** — Aplicar el cambio en el archivo correspondiente
4. **Probar manualmente** — Cada interfaz requiere prueba visual o funcional directa
5. **Verificar retrocompatibilidad** — Asegurar que los cambios no rompan otras interfaces

## Checklist rápido

- [ ] Los componentes de UI no importan lógica de core/ directamente (deben pasar por brain o módulos intermedios)
- [ ] `atlas_ui.py` usa `st.session_state` para toda la UI; no persistir estado en variables globales
- [ ] La API `POST /chat` retorna `StreamingResponse` de texto plano; no romper el formato
- [ ] Los comandos `!` en CLI y UI web deben tener la misma implementación
- [ ] Los secretos (API keys) no deben exponerse en la UI ni en respuestas de la API
- [ ] Los cambios en `run.bat` / `run_ui.bat` deben probarse en Windows sin `.venv`

## Gotchas / Riesgos

- **Streamlit sin estado compartido**: Cada interacción recarga el script; todo el estado debe estar en `st.session_state`
- **Streaming asíncrono**: En `atlas_ui.py`, el streaming se hace en un hilo daemon con `Queue`; si la cola se bloquea, la UI se congela
- **API sin autenticación**: Todos los endpoints de FastAPI son públicos; no agregar credenciales sin capa de seguridad
- **CLI interactivo**: Usa `input()` directo; no hay manejo de señales ni `readline` avanzado
- **Entry points duplicados**: La misma funcionalidad existe en CLI y UI web; los bugs pueden aparecer en solo una interfaz

## Relaciones

- `nucleo-atlas` → Si se exponen nuevos parámetros de brain, router o streaming en la UI
- `base-conocimiento` → Si se agregan comandos o UI para ingesta/consulta RAG
- `configuracion-sistema` → Si se modifican entry points, scripts de arranque o paneles de sistema
- `multimodal` → Si se integran comandos de voz, visión o captura en la interfaz

## Archivos relacionados

- `references/KNOWLEDGE.md` — Mapa de módulos de la UI, notas técnicas y riesgos

## Validación

- **CLI**: `python run.py` — probar comandos `!` y flujo conversacional completo
- **Web UI**: `streamlit run atlas_ui.py` — revisar sidebar, métricas, chat, comandos, selectores
- **API**: `uvicorn main_api:app --reload` — probar `GET /`, `GET /chats`, `POST /chat` con curl
- **Entry points**: Ejecutar `run.bat` y `run_ui.bat` desde terminal limpia
