# Interfaz de Usuario — Conocimiento técnico

## Mapa de módulos

| Archivo | Rol |
|---|---|
| `atlas_ui.py` | Aplicación Streamlit (1666 líneas): sidebar, chat, comandos, streaming |
| `atlas_chat.py` | CLI interactivo (785 líneas): input loop, comandos, voz |
| `main_api.py` | API REST FastAPI (122 líneas): 6 endpoints, streaming |
| `run.py` | Entry point CLI (8 líneas, delega a atlas_chat.chat()) |
| `run.bat` / `run_ui.bat` | Launchers Windows con detección de Python |

## Notas técnicas

- `atlas_ui.py` usa `st.session_state` para todo el estado de UI. No hay variables globales de UI.
- El streaming en Streamlit usa un hilo daemon + `Queue` para comunicación entre hilos.
- `main_api.py` no tiene autenticación. Todos los endpoints son públicos.
- Los comandos `!` en CLI y UI web deben tener implementación consistente.
- Los entry points detectan `.venv` primero, luego `py -3.13..3.11`, luego global.

## Riesgos

- **Streamlit sin estado compartido**: Cada interacción recarga el script; el estado debe vivir en `st.session_state`.
- **Streaming asíncrono**: Si la `Queue` se bloquea, la UI se congela sin mensaje de error.
- **API sin auth**: Todos los endpoints de FastAPI son públicos.
- **Comandos `!` duplicados**: La lógica de comandos existe tanto en CLI como UI; pueden divergir.
