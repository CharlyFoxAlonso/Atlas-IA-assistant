# Núcleo de Atlas — Conocimiento técnico

## Mapa de módulos

| Archivo | Rol |
|---|---|
| `core/brain.py` | Orquestador: streaming híbrido, historial deslizante, interceptación de reglas |
| `core/router.py` | Clasificador LLM de intención → 5 agentes |
| `core/models.py` | Gateway no-streaming a Ollama / NVIDIA |
| `core/config.py` | Catálogo de modelos, parámetros RAG, detección HW |
| `core/chat_manager.py` | Sesiones múltiples de chat con persistencia JSON |
| `core/temp_rules.py` | Reglas de contenido (interceptadas) y formato (inyectadas) |
| `core/reflection.py` | Análisis de conversaciones, detección de patrones |
| `core/self_awareness.py` | Informes técnicos de auto-conocimiento |
| `core/self_improvement.py` | Búsqueda web y persistencia de recomendaciones de mejora |

## Flujo de ejecución

1. `pensar_con_streaming()` recibe `(pregunta, motor, modelos...)`.
2. `verificar_reglas_y_forzar_respuesta()` evalúa reglas de contenido. Si coincide, retorna respuesta forzada sin llamar al LLM.
3. `cargar_perfil_charly()` + `formatear_historial()` arman contexto de usuario.
4. `obtener_reglas_de_formato()` extrae reglas a inyectar en el prompt.
5. `detectar_agente_con_modelo()` clasifica intención. `cargar_prompt_agente()` obtiene identidad.
6. Según agente: `researcher` busca RAG + web; `estadistica` busca solo RAG; otros usan prompt + perfil.
7. Ensamblado de contexto final con instrucciones y reglas.
8. `motor` determina streaming: `atlas` (Ollama HTTP), `prometeo` (OpenAI SDK), `groq` (Groq SDK).
9. `agregar_al_historial()` persiste la interacción en `HISTORIAL`.

## Invariantes arquitectónicos

- **Brain no depende de interfaces de usuario.** Solo importa módulos de `core/` y librerías estándar. No debe importar Streamlit, FastAPI ni ningún módulo de UI.
- **Router solo clasifica intenciones.** No implementa lógica de negocio. Su alcance se limita a seleccionar agente y cargar prompts de identidad.
- **Los nombres de agente en router deben coincidir** con archivos `agente_{nombre}.md` en Prompts.

## Deudas y restricciones actuales

- **Acceso LLM no centralizado.** Brain implementa streaming directo a Ollama, NVIDIA y Groq. `digestion_worker` y `exam_mode` también tienen clientes propios.
- **Sin abstracción común de streaming.** Cada `_stream_*` en brain.py tiene su propia implementación y manejo de errores.
- **Historial global mutable.** `HISTORIAL` es una lista global modificable desde cualquier lugar.
- **Reglas temporales volátiles.** `REGLAS_TEMPORALES` se pierde al reiniciar el proceso.
- **Config sin persistencia.** Los cambios en `config.py` no se guardan en `.env` automáticamente.

## Riesgos conocidos detallados

- **API key faltante**: Brain valida `NVIDIA_API_KEY` o `GROQ_API_KEY` recién al llamar. El error aparece en stream como `yield "❌ Error..."`.
- **Ollama caído**: `_stream_local()` falla con timeout de 120s sin reintentos.
- **Historial corrupto**: Si un ítem de `HISTORIAL` no tiene `pregunta`/`respuesta`, `formatear_historial()` falla.
- **Chat ID inválido**: `chat_manager.py` no valida formato. ID inexistente devuelve `None`.
- **Reglas sin límite**: `REGLAS_TEMPORALES` puede crecer sin control. Solo `limpiar_reglas()` lo resetea.
- **Streaming asíncrono en Streamlit**: El hilo daemon lanza chunks a una `Queue`; el hilo principal los renderiza por polling. Si la cola se llena, la UI se congela.
