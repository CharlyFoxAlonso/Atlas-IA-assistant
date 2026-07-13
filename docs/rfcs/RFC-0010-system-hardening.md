# RFC-0010: Endurecimiento y cierre técnico de `core/system`

**Estado:** Aceptado e implementado  
**Sprint:** Sprint 0  
**Fecha:** 2026-07-13

## Contexto

Doctor, Healer, Launcher y la CLI ya funcionaban, pero quedaban diferencias entre perfiles de arranque, validación superficial de paquetes, logs no persistentes y casos de borde de subprocess en Windows.

## Decisiones

### Entorno virtual

El `.venv` actual se conserva. Su configuración apunta correctamente a Python 3.13.14 y la UI funciona en el contexto del usuario. El error de ejecución desde Codex se atribuye al sandbox, que no puede ejecutar el Python base ubicado en AppData.

No se recreará un entorno funcional para resolver una limitación de automatización.

### CommandRunner

- Decodifica salidas `bytes` de timeouts con fallbacks de Windows.
- Redacta secretos explícitos, variables sensibles, credenciales en URL y Bearer tokens.
- Detecta procesos que terminan durante una ventana inicial configurable.
- Conserva listas de argumentos y `shell=False`.

### Perfiles de preparación

Doctor diferencia `ui`, `cli` y `api`. `ready_to_start` refleja el perfil seleccionado y `startup_profiles` contiene el panorama completo.

Los perfiles reflejan los imports inmediatos del código actual. Pillow y PyAutoGUI forman parte de los tres perfiles porque `core.vision` se importa al iniciar UI, CLI y API, aunque la utilización efectiva de visión sea opcional.

Launcher solicita el perfil `ui` o `cli` según el destino.

### Paquetes

La validación normal usa metadatos y es apta para cada rerender de Streamlit. La validación profunda, activada con `doctor --deep`, importa únicamente los requisitos del perfil en procesos aislados.

Los estados son:

- `missing`;
- `found`;
- `importable`;
- `broken`.

### Auditoría operativa

Las operaciones reales generan JSONL rotativo en `logs/atlas-system.log`. Las simulaciones permanecen sin efectos secundarios. Los campos sensibles se redactan antes de persistir.

### CLI

Se admite tanto `--help` como:

```text
python -m core.system help
python -m core.system help doctor
python -m core.system help heal
python -m core.system help launch
```

Los códigos de salida también se verifican mediante procesos Python reales.

## Consecuencias

- El diagnóstico rápido sigue siendo adecuado para la UI.
- Soporte técnico puede solicitar un diagnóstico profundo sin contaminar el proceso principal.
- CLI y UI ya no comparten falsamente el mismo requisito de Streamlit.
- Los procesos que fallan inmediatamente dejan un resultado útil.
- Las reparaciones reales quedan auditadas sin publicar secretos.

## Fuera de alcance

- Reconstrucción de `.venv`.
- Descarga verificada de runtimes o ejecutables.
- Instalador final.
- Actualización automática.
- Refactors fuera de `core/system`.
