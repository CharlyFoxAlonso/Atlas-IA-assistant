---
name: calidad-proyecto
# process: metodología de calidad, no modifica un módulo específico sino que evalúa
#          el estado del proyecto transversalmente
type: process
description: |
  Calidad y mantenimiento de Atlas: tests, linting, tipado, CI/CD, documentación,
  dependencias, limpieza de código muerto y archivos huérfanos.
  Usar al mejorar la salud técnica y la mantenibilidad del repositorio.
  No usar para desarrollar funcionalidad nueva o modificar la lógica del sistema.
---

# Calidad del Proyecto

## Propósito

Mantener la salud del proyecto mediante tests, linting, type checking, limpieza de código huérfano, gestión de agentes y documentación técnica.

## Cuándo usarla

- El usuario pide ejecutar tests, agregar tests o diagnosticar cobertura
- El usuario solicita linting, type checking o formateo de código
- El usuario reporta código muerto, importaciones no utilizadas o archivos huérfanos
- El usuario pide configurar CI/CD, pre-commit hooks o herramientas de calidad
- El usuario solicita mejorar la documentación técnica o actualizar dependencias

## Cuándo no usarla

- Desarrollo de funcionalidad nueva → la skill del dominio correspondiente
- Bug fixes en lógica existente → la skill del módulo afectado
- Refactorización que cambia comportamiento → `auditoria` primero

## Procedimiento

1. **Comprender el estado actual** — Revisar `tests/`, buscar configs de herramientas de calidad (`pyproject.toml`, `setup.cfg`, `.github/`)
2. **Ejecutar tests existentes** — `python -m unittest discover tests` para verificar que todo pasa
3. **Si no hay herramientas** — Proponer configuración gradual (empezar con ruff para linting, después mypy para tipado)
4. **Identificar código huérfano** — Buscar importaciones no utilizadas, funciones sin referencias, archivos sin imports
5. **Documentar deuda técnica** — Si se encuentra código muerto o áreas sin test, documentarlo en lugar de eliminarlo sin autorización
6. **Validar** — Los cambios de calidad no deben romper funcionalidad existente

## Checklist rápido

- [ ] Los tests existentes usan `unittest`, no `pytest` — mantener consistencia
- [ ] No existe `pyproject.toml`, `setup.cfg` ni ninguna configuración de herramientas de calidad
- [ ] No hay CI/CD configurado (ni `.github/`, ni `.gitlab-ci.yml`)
- [ ] No hay TODO/FIXME/HACK markers en el código (el español "TODO" en comentarios es falso positivo)
- [ ] Solo `core/system/` y `core/web_crawler.py` tienen tests
- [ ] `core/brain.py`, `core/config.py`, `core/vector_store.py`, `agents/`, `atlas_ui.py`, `main_api.py` no tienen tests

## Reglas

- Los tests existentes usan `unittest`, no `pytest` — mantener consistencia
- No existe `pyproject.toml`, `setup.cfg` ni ninguna configuración de herramientas de calidad
- No hay CI/CD configurado (ni `.github/`, ni `.gitlab-ci.yml`)
- Solo `core/system/` y `core/web_crawler.py` tienen tests
- No modificar archivos de tests sin verificar que el cambio no rompa la suite existente

## Gotchas / Riesgos

- **Sin cobertura**: No hay medición de code coverage
- **Dependencias sin fijar**: `requirements.txt` es el único mecanismo
- **Sin type checking**: `core/system/` tiene type hints pero no se verifican
- **Pruebas manuales**: La mayor parte del proyecto se valida manualmente
- **Sin pre-commit**: No hay barreras para commits con código de baja calidad

## Relaciones

- `auditoria` → Antes de cambios mayores de calidad, ejecutar auditoría completa
- `configuracion-sistema` → Si se instalan herramientas de calidad (ruff, mypy, pytest) como dependencias
- Todas las demás skills → Los tests y calidad aplican a todos los módulos

## Validación

- **Tests**: `python -m unittest discover tests -v` — ejecuta todos los tests y muestra resultados
- **Linting**: Si se configura ruff, `ruff check .` (o la herramienta elegida)
- **Type checking**: Si se configura mypy, `mypy core/` para verificar tipos
- **Código muerto**: `python -c "import os; [print(f) for f in os.listdir('core/') if f.endswith('.py')]"` para listar módulos y verificar imports cruzados
- **Dependencias**: Revisar `requirements.txt` vs imports reales con `pip freeze` y `importlib`

## Formato de salida

Archivos de test modificados o creados, cobertura estimada (si se midió), herramientas de calidad configuradas, cambios en dependencias, código muerto identificado y acciones realizadas.
