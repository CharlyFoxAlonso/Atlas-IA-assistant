# Desarrollo y operación técnica de Atlas

## Entorno soportado

- Windows 11 como plataforma principal inicial.
- Python 3.11, 3.12 o 3.13.
- Entorno virtual local `.venv`.
- PowerShell o CMD para tareas técnicas.

No usar Python 3.14 para instalar el conjunto completo de dependencias hasta confirmar compatibilidad de ChromaDB, Torch y Sentence Transformers.

## Preparación manual de desarrollo

Desde la raíz del repositorio:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

La creación o reconstrucción del entorno es una acción de desarrollo. Healer no reemplaza automáticamente un `.venv` existente.

## Configuración local

Crear la configuración privada a partir del ejemplo versionado:

```powershell
Copy-Item .env.example .env
```

Las claves de proveedores son opcionales. Deben dejarse vacías cuando no se utilicen; Atlas puede operar con Ollama sin claves de nube. `.env` está excluido de Git y `.env.example` nunca debe contener secretos reales.

## CLI del subsistema

Mostrar ayuda:

```powershell
python -m core.system
python -m core.system --help
python -m core.system help
python -m core.system help doctor
python -m core.system help heal
python -m core.system help launch
```

Diagnosticar:

```powershell
python -m core.system doctor
python -m core.system doctor --profile cli
python -m core.system doctor --profile api
python -m core.system doctor --profile ui --deep
python -m core.system doctor --json
```

`--deep` prueba los imports requeridos por el perfil en procesos aislados. No importa Torch, ChromaDB ni otros paquetes pesados que no formen parte del arranque seleccionado.

Simular reparaciones:

```powershell
python -m core.system heal
python -m core.system heal folders
python -m core.system heal config --json
```

Aplicar reparaciones seguras:

```powershell
python -m core.system heal folders --apply
python -m core.system heal config --apply
python -m core.system heal ollama_service --apply
```

Las instalaciones y descargas pesadas exigen doble consentimiento:

```powershell
python -m core.system heal python_packages --apply --allow-heavy
python -m core.system heal ollama_model --apply --allow-heavy
```

Simular o efectuar el arranque:

```powershell
python -m core.system launch
python -m core.system launch --target cli
python -m core.system launch --target ui --port 8401 --apply
```

El contrato de puertos de `run_ui.bat` depende de la ruta de runtime: el
intérprete local `.venv` inicia la UI en el puerto principal `8401`; si ese
intérprete no existe, las rutas de respaldo con `py` o Streamlit global usan
`8501`. El batch no selecciona el fallback comprobando si `8401` está ocupado.

## Códigos de salida

| Código | Significado |
|---:|---|
| `0` | Operación correcta |
| `1` | Sistema no listo o advertencias relevantes |
| `2` | Argumentos inválidos o consentimiento insuficiente |
| `3` | Reparación o lanzamiento fallido |

Los scripts externos deben usar estos códigos y no analizar texto humano. Para integración programática se recomienda `--json`.

## Uso desde CMD y PowerShell

Los comandos se ejecutan desde la raíz del repositorio mientras Atlas no esté instalado como aplicación.

CMD:

```bat
cd /d <ruta-del-repo>
.venv\Scripts\activate.bat
python -m core.system help
```

PowerShell:

```powershell
Set-Location <ruta-del-repo>
.\.venv\Scripts\Activate.ps1
python -m core.system help
```

También se puede evitar la activación y llamar al intérprete directamente:

```powershell
.\.venv\Scripts\python.exe -m core.system doctor --profile ui
```

## Logs operativos

Las operaciones reales de Healer y Launcher se registran en:

```text
logs/atlas-system.log
```

El formato es JSON Lines, con timestamp UTC, identificador de evento y rotación de 2 MiB con tres respaldos. Las simulaciones no crean logs y los campos sensibles se redactan.

## Ejecutar pruebas

Las pruebas usan `unittest` y mocks. No descargan ni instalan software:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q core\system tests
```

Cobertura mínima actual:

- contratos JSON;
- rutas de desarrollo y empaquetadas;
- comandos, timeout y redacción;
- GPU y Ollama ausentes o fallando;
- claves presentes sin exponer valores;
- capacidades degradadas;
- reparaciones en simulación;
- consentimiento e idempotencia;
- fallo parcial de Healer;
- coordinación de Launcher;
- CLI, códigos de salida y JSON válido.

## Desarrollo de integraciones

Los consumidores Python deben usar las APIs y no ejecutar la CLI como subproceso:

```python
from core.system import Healer, Launcher, diagnosticar_sistema

diagnosis = diagnosticar_sistema()
simulation = Healer(dry_run=True).fix("folders")
launch_plan = Launcher(dry_run=True).launch(target="ui")
```

La CLI está pensada para operadores, scripts y diagnóstico técnico. Una futura vista de Streamlit debe importar estas mismas APIs.

## Reglas de seguridad para contribuciones

- No usar `shell=True`.
- No aceptar comandos arbitrarios del usuario.
- No imprimir ni registrar valores de claves.
- No realizar cambios al importar módulos.
- Mantener `dry_run=True` por defecto.
- No ejecutar instalaciones reales en tests.
- No elevar privilegios silenciosamente.
- No mover ni borrar memoria privada.
- Agregar tests antes de exponer una reparación nueva en la CLI o UI.

## Problemas conocidos

- El `.venv` está configurado correctamente con Python 3.13.14. El “Acceso denegado” observado ocurre solamente dentro del sandbox de Codex porque el Python base reside fuera de su ámbito ejecutable; no justifica reconstruir el entorno.
- La captura de consola PowerShell puede representar incorrectamente algunos caracteres Unicode; JSON conserva Unicode válido.
- La memoria y varias rutas del código histórico siguen siendo relativas al repositorio.
- Todavía no existe migración automática de datos ni instalador de usuario final.
