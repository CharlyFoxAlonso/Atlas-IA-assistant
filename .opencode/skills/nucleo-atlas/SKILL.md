---
name: nucleo-atlas
# domain: modifica orquestación central (Brain, Router, streaming, historial)
type: domain
description: |
  Modifica o diagnostica la orquestación central de Atlas: Brain, Router, streaming,
  historial, chat_manager, reglas temporales y auto-reflexión.
  Usar cuando el cambio afecte cómo Atlas genera respuestas, clasifica intenciones o
  gestiona sesiones. No usar para RAG, interfaz de usuario ni instalación del sistema.
---

# Núcleo de Atlas

## Propósito

Guiar a OpenCode cuando la tarea afecte cómo Atlas genera respuestas, clasifica intenciones, gestiona sesiones de chat, se comunica con proveedores LLM, aplica reglas temporales o reflexiona sobre su comportamiento.

## Cuándo usarla

- El usuario menciona brain, router, streaming, historial, regla temporal, reflexión, auto-conocimiento, auto-mejora, motor (atlas/prometeo/groq)
- El usuario pide modificar generación de respuestas, enrutamiento o proveedor LLM
- El usuario reporta respuestas incorrectas, lentas o que no llegan
- El usuario solicita cambiar configuración de modelos en runtime

## Cuándo no usarla

- Búsqueda semántica, ChromaDB o indexación → `base-conocimiento`
- Interfaz gráfica, CLI, API REST → `interfaz-usuario`
- Instalación, dependencias, arranque, backup → `configuracion-sistema`
- Análisis transversal del proyecto → `auditoria`

## Workflow

1. **Comprender** — Leer el módulo relevante. Si no conoces la arquitectura interna, lee `references/KNOWLEDGE.md`.
2. **Detectar impacto** — Evaluar qué otros módulos consumen lo que se va a cambiar. Por ejemplo, `chat_manager.py` usa `brain.HISTORIAL`.
3. **Preservar invariantes** — Verificar que el cambio no rompa los invariantes listados en `references/KNOWLEDGE.md`.
4. **Modificar** — Aplicar el cambio en el archivo correspondiente.
5. **Validar** — Probar según el módulo modificado (ver Validación abajo).
6. **Documentar** — Si aparecen nuevas deudas, registrarlas. Si se modifica el flujo, actualizar `references/KNOWLEDGE.md`.

## Checklist rápido

- [ ] Brain no importará UI, FastAPI ni Streamlit
- [ ] Router no agregará lógica de negocio ni búsquedas
- [ ] `HISTORIAL` conservará el formato `[{pregunta, respuesta}]`
- [ ] La interceptación de reglas se ejecutará antes de la llamada al LLM
- [ ] Los nombres de agente en router coincidirán con archivos `agente_{nombre}.md`
- [ ] `chat_manager` preservará la estructura JSON `{id, nombre, creado, motor, messages, historial_brain}`
- [ ] Las reglas de contenido seguirán usando substring match (`in`)
- [ ] Los cambios en `config.py` no persistirán en `.env` (usar `set_modelo_local()` para runtime)
- [ ] `models.py` no agregará modo `groq` (está en brain.py)

## Gotchas / Riesgos

- **API key faltante**: El error aparece recién al llamar al LLM, no al iniciar
- **Ollama caído**: Timeout de 120s sin reintentos automáticos
- **Historial mutable**: Es una lista global; cualquier módulo puede modificarla
- **Chat ID inválido**: `chat_manager.py` no valida formato; ID inexistente devuelve `None`
- **Reglas sin límite**: `REGLAS_TEMPORALES` puede crecer sin control

## Relaciones

- `base-conocimiento` → Si el cambio afecta cómo brain.py consulta el RAG o la web
- `configuracion-sistema` → Si requiere descargar un modelo, instalar dependencias o modificar el entorno
- `interfaz-usuario` → Si el cambio expone nuevos parámetros en UI, CLI o API
- `auditoria` → Antes de cambios mayores que puedan afectar la arquitectura general

## Archivos relacionados

- `references/KNOWLEDGE.md` — Mapa de módulos, flujo de ejecución, invariantes, deudas, riesgos detallados

## Validación

- **brain.py / router.py / models.py** → `python run.py` con pregunta-respuesta en distintos motores
- **config.py** → `python -m core.system doctor` confirma diagnóstico. `python core/config.py` imprime configuración
- **chat_manager.py** → Crear, cambiar y restaurar sesiones. Verificar persistencia JSON
- **temp_rules.py** → Agregar reglas y verificar interceptación desde CLI
- **reflection.py / self_awareness.py / self_improvement.py** → Ejecutar la función modificada y verificar salida

## Formato de respuesta

Archivos modificados, invariantes respetados o deudas documentadas, validación realizada, efectos colaterales en otras skills.

## Reglas de seguridad

- No exponer API keys en logs, outputs ni mensajes de error visibles
- No modificar `HISTORIAL` sin mantener el contrato `{pregunta, respuesta}`
- No eliminar archivos de prompt del sistema
