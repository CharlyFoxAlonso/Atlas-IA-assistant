# Atlas Auditor — entorno de desarrollo aislado

Atlas Auditor se desarrolla en el worktree `C:\Users\delfa\Documents\Atlas-Auditor`, asociado exclusivamente a la rama `atlas-auditor`.

## Aislamiento

- Entorno virtual: `C:\Users\delfa\Documents\Atlas-Auditor\.venv`
- Datos de prueba: `C:\Users\delfa\Documents\Atlas-Auditor\memory\Atlas_Auditor_Test`
- Memoria de Atlas Personal: permanece en `C:\Users\delfa\Documents\Atlas\memory\Atlas_Memory`
- La carpeta de datos de prueba está excluida de Git.

No se debe copiar el `.venv`, el archivo `.env`, la base vectorial ni la memoria de Atlas Personal al worktree de Auditor.

## Estructura local de prueba

```text
memory/Atlas_Auditor_Test/
├── 00_Sistema/
├── 01_Perfil/
├── 02_Conocimientos/
└── 03_Biblioteca/
```

## Variables locales recomendadas

Estas variables pueden definirse en un `.env` local no rastreado cuando Atlas Auditor empiece a consumir la nueva ruta:

```dotenv
ATLAS_DATA_DIR=C:\Users\delfa\Documents\Atlas-Auditor
ATLAS_MEMORY_DIR=C:\Users\delfa\Documents\Atlas-Auditor\memory\Atlas_Auditor_Test
```

El subsistema `core/system` ya reconoce ambas variables. Los módulos heredados que todavía usan `memory/Atlas_Memory` deberán migrarse mediante un RFC de Atlas Auditor antes de operar con datos reales.

## Activación

```powershell
cd C:\Users\delfa\Documents\Atlas-Auditor
.\.venv\Scripts\Activate.ps1
python -m core.system doctor
```
