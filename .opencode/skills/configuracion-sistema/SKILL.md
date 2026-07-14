---
name: configuracion-sistema
# domain: instalación, diagnóstico, reparación del runtime, scripts del sistema
type: domain
description: |
  Instalación, configuración, diagnóstico y reparación del runtime de Atlas.
  Usar cuando haya problemas de entorno Python, dependencias, Ollama, rutas,
  variables de entorno, arranque, backup o restauración.
  No usar para modificar lógica del núcleo, RAG o interfaces de usuario.
---

# Configuración del Sistema

## Propósito

Diagnosticar, reparar y mantener el entorno de ejecución de Atlas, incluyendo instalación, dependencias, servicios, rutas, variables de entorno y scripts de backup/restauración.

## Cuándo usarla

- El usuario reporta errores de arranque, importación, dependencias o entorno
- El usuario necesita diagnóstico del sistema (doctor), reparaciones (healer) o arranque (launcher)
- El usuario pide backup, restauración o distribución del proyecto
- El usuario solicita cambiar configuración de entorno (API keys, rutas, modelos)
- El usuario requiere descargar/eliminar modelos de Ollama

## Cuándo no usarla

- Problemas en la generación de respuestas o enrutamiento → `nucleo-atlas`
- Problemas en búsqueda semántica o indexación → `base-conocimiento`
- Modificaciones en la UI, CLI o API → `interfaz-usuario`

## Workflow

1. **Diagnosticar** — Ejecutar `python -m core.system doctor` (o `!doctor` desde CLI). Identificar el estado actual
2. **Identificar** — Localizar el componente afectado: dependencias, Ollama, carpetas, config, herramientas externas
3. **Reparar (dry-run)** — `python -m core.system heal <componente>` para simular sin aplicar cambios
4. **Reparar (real)** — `python -m core.system heal <componente> --apply` (agregar `--allow-heavy` si requiere instalaciones)
5. **Verificar** — Re-ejecutar doctor para confirmar que el problema está resuelto
6. **Si no hay arreglo automático** — Leer `references/KNOWLEDGE.md` para entender la arquitectura del subsistema

## Checklist rápido

- [ ] Usar `--apply` solo cuando el usuario lo autorice explícitamente
- [ ] Verificar que `--apply` sin `--allow-heavy` no ejecuta instalaciones ni descargas
- [ ] `pip install -r` está bloqueado en Python global (requiere venv + heavy)
- [ ] Las rutas varían entre development y packaged — verificar modo con `AtlasPaths`
- [ ] Los secretos en `.env` no deben exponerse en logs ni outputs
- [ ] Después de backup, verificar que el ZIP contiene `core/`, `memory/`, `vector_db/`, `*.py`, `.env`
- [ ] El log de auditoría está en `{logs_dir}/atlas-system.log`

## Gotchas / Riesgos

- **Healer no modifica `.env` existente** — Solo crea uno nuevo si no existe; no actualiza claves
- **Ollama service puede no iniciar** si el binario no está en PATH o el puerto 11434 está ocupado
- **`--allow-heavy` es necesario para `pip install` y `ollama pull`** — sin esta flag, esas reparaciones se omiten aunque se use `--apply`
- **Backup no incluye `.venv/`** — Las dependencias se reinstalan con `pip install -r`
- **Restauración sin `.env`** — El script advierte pero no bloquea; el sistema se inicia sin API keys

## Relaciones

- `nucleo-atlas` → Si el cambio requiere modificar configuración de modelos en runtime
- `base-conocimiento` → Si se requieren dependencias para ChromaDB o nuevos paquetes RAG
- `interfaz-usuario` → Si se modifican entry points, scripts de arranque o comandos del sistema
- `auditoria` → Antes de cambios mayores en la infraestructura del sistema

## Archivos relacionados

- `references/KNOWLEDGE.md` — Mapa de módulos del sistema, resolución de rutas, composición de doctor/healer, variables de entorno, invariantes

## Validación

- **Doctor**: `python -m core.system doctor --json` confirma estado. `--profile ui|cli|api` verifica perfiles específicos
- **Healer**: `python -m core.system heal all --json` simula reparaciones. Agregar `--apply` para ejecutar
- **Launcher**: `python -m core.system launch --target cli --apply` arranca Atlas
- **Backup**: Ejecutar `python scripts/backup_atlas.py` y verificar contenido del ZIP
- **Restore**: Ejecutar `python scripts/restaurar_atlas.py` y verificar que los archivos se restauran
- **Config**: `python core/config.py` imprime la configuración completa
