# Auditoría general — Portabilidad e instalación reproducible de Atlas

Fecha: 2026-07-24
Tipo: General
Repositorio: C:\Users\delfa\Documents\Atlas
Rama: atlas-v4.1-incremental-indexing
Commit auditado: c842d66
Archivo: docs/reviews/general/2026-07-24-c842d66-general-portability-and-reproducible-installation-review.md
Estado general: PARTIAL

## 1. Resumen ejecutivo

Atlas funciona correctamente en la PC del desarrollador con setup manual, pero hoy no es instalable ni reproducible en otra PC Windows de forma automática. Existe una política central de rutas (`core/system/paths.py`) bien diseñada y probada, pero no está conectada al código productivo (brain, config, vector_store, memory_manager, chat_manager, etc.), que sigue usando rutas relativas hardcodeadas dependientes del current working directory. Existe un instalador (`Atlas_Installer.bat`) rastreado en git pero inconsistente con la documentación y los launchers: instala Python 3.11 (no 3.13), no crea `.venv`, no crea `.env`, no crea estructura de memoria, no verifica Poppler/FFmpeg, y lanza Streamlit sin puerto. No existe lockfile reproducible. No existe evidencia de validación en PC limpia. La aplicación y los datos del usuario no están separados en modo desarrollo.

El hallazgo central sobre rutas se clasifica como HIGH — bloquea el objetivo auditado de instalación reproducible, pero no impide el funcionamiento actual de Atlas en modo desarrollo cuando se lanza desde la raíz del repositorio.

## 2. Objetivo

Determinar, mediante evidencia directa del repositorio, qué impide hoy que Atlas pase de funcionar correctamente en la computadora del desarrollador a poder empaquetarse, instalarse y ejecutarse de forma reproducible en otra PC con Windows 10/11.

## 3. Alcance

Repositorio Atlas en rama `atlas-v4.1-incremental-indexing`, HEAD `c842d66`. Inspección de rutas, runtime, dependencias, herramientas externas, instalador, launchers, scripts de distribución, doctor/healer/launcher, tests de sistema, documentación pública.

## 4. Fuera de alcance

Datos privados (`memory/`, `vector_db/`, `.env`), ejecución de Ollama real, descarga de modelos, APIs pagas, instalación en PC limpia real, empaquetado con PyInstaller/PyOxidator.

## 5. Estado Git

| Campo | Valor |
|---|---|
| Repositorio | `C:\Users\delfa\Documents\Atlas` |
| Rama | `atlas-v4.1-incremental-indexing` |
| HEAD | `c842d666f50bd15b84e62569b91bfab2f6fd7d78` |
| Tracking | `origin/atlas-v4.1-incremental-indexing` (up to date) |
| Working tree | limpio |
| Archivos modificados | ninguno |
| Archivos no rastreados | ninguno |
| `AGENTS.md` | no existe; instrucciones aplicables: `.opencode/project-identity.md` |

Nota: el usuario esperaba HEAD `9caf3af`, que es el commit padre. El HEAD avanzó 1 commit con `refactor(opencode): focus Atlas planner on implementation planning`. Esto no afecta el alcance de portabilidad.

## 6. Instrucciones aplicables

- `.opencode/project-identity.md`: define stack, entry points, convenciones, invariantes arquitectónicas, principios local-first/privacy-first.
- Sin `AGENTS.md` en raíz ni subdirectorios.

## 7. Entorno

- Intérprete venv: `.venv\Scripts\python.exe` → Python 3.13.14
- Plataforma: win32, Windows 10/11
- Tests ejecutados con venv local

## 8. Áreas inspeccionadas

- `core/system/paths.py`, `doctor.py`, `healer.py`, `launcher.py`, `__main__.py`
- `core/config.py`, `vector_store.py`, `pdf_reader.py`, `audio_transcriber.py`, `security.py`, `speech_input.py`
- `run.py`, `run.bat`, `run_ui.bat`, `Atlas_Installer.bat`
- `scripts/crear_distribucion.py`, `limpiar_para_distribuir.py`, `backup_atlas.py`, `restaurar_atlas.py`
- `README.md`, `SETUP.md`, `.env.example`, `requirements.txt`
- Tests: `test_system_foundations`, `test_system_cli`, `test_launcher`, `test_healer`, `test_operational_log`, `test_configuration_hygiene`

## 9. Evidencia

### Tests ejecutados (SAFE TO RUN)

Comando: `.venv\Scripts\python.exe -m unittest tests.test_system_foundations tests.test_system_cli tests.test_launcher tests.test_healer tests.test_operational_log tests.test_configuration_hygiene -v`

- Intérprete: Python 3.13.14 (venv)
- Resultado: 52 tests, 0 failures, 0 errors, 0 skipped
- Aislamiento: usan `TemporaryDirectory`, mocks, no tocan `memory/`, `vector_db/`, `.env`, Ollama ni APIs
- Working tree posterior: limpio

### Búsquedas Git

- `git grep "memory/Atlas_Memory"` → 60 coincidencias en código productivo (rutas relativas hardcodeadas)
- `git grep "os.getcwd|Path.cwd"` → 15 coincidencias (dependencia de CWD)
- `git grep "from core.system.paths|AtlasPaths|get_paths"` → solo en `core/system/` y `tests/` (NO en código productivo de Atlas)
- `git ls-files | findstr Atlas_Installer` → `Atlas_Installer.bat` SÍ rastreado
- `git ls-files | findstr lock` → sin lockfile

## 10. Hallazgos

### HIGH — Rutas relativas no conectadas a la política central (B-01)

Severidad: HIGH — bloquea el objetivo auditado de instalación reproducible. No impide el funcionamiento actual de Atlas en modo desarrollo cuando se lanza desde la raíz del repositorio.

Archivo: `core/config.py`, `core/vector_store.py`, `core/brain.py`, `core/memory_manager.py`, `core/chat_manager.py`, `core/router.py`, `core/security.py`, `core/diary_manager.py`, `core/vision.py`, `core/self_awareness.py`, `core/profile_manager.py`, `core/speech_input.py`, `core/self_improvement.py`, `core/ingestion_manager.py`, `core/local_ingestion_manager.py`, `agents/export_study.py`

Símbolo: constantes `BASE_MEMORIA`, `BASE_ESTUDIO`, `BASE_PROMPTS`, `CHROMA_PATH`, `CHATS_DIR`, `DIARIO_PATH`, `CAPTURAS_DIR`, `VOSK_MODEL_DIR`, `RAG_BASE_PATH`, etc.

Problema: El código productivo de Atlas usa rutas relativas hardcodeadas (`"memory/Atlas_Memory"`, `"./vector_db"`, `"memory/Atlas_Memory/chats"`, etc.) que se resuelven contra el CWD. La política central `core/system/paths.py` existe y soporta modo `packaged` (separando programa de datos en `%LOCALAPPDATA%/Atlas`), pero no es importada ni usada por ningún módulo productivo. Solo `doctor`, `healer`, `launcher` y `operational_log` la usan.

Evidencia: `git grep "from core.system.paths"` devuelve solo `core/system/doctor.py`, `healer.py`, `launcher.py`, `operational_log.py` y tests. `core/config.py:184-187` define `BASE_MEMORIA = "memory/Atlas_Memory"` y `CHROMA_PATH = "./vector_db"`. `core/vector_store.py:15` redefine `CHROMA_PATH = "./vector_db"`. 60 coincidencias de `memory/Atlas_Memory` en código productivo.

Impacto: Atlas solo funciona si se lanza desde la raíz del repositorio. Si se empaqueta con `paths.py` modo `packaged`, los datos se irían a `%LOCALAPPDATA%/Atlas` pero el código productivo seguiría escribiendo en `./memory` y `./vector_db` relativos al CWD. Incompatible con instalación reproducible.

Corrección mínima: Conectar `core/config.py` (y consumidores) con `core.system.paths.get_paths()`, reemplazando las constantes relativas por rutas derivadas de `AtlasPaths`. Mantener modo `development` por defecto para no romper el setup actual. Esta migración es el objetivo general, pero el planner deberá dividirla en cortes pequeños según los consumidores y contratos reales de cada módulo.

Prueba de aceptación: Un test lanza Atlas con `ATLAS_DATA_DIR` apuntando a un temp dir y verifica que `memory/`, `vector_db/`, logs y chats se escriban allí, no en CWD.

Estado: CONFIRMED BY CODE INSPECTION

### HIGH — Instalador inconsistente con la documentación (H-01)

Severidad: HIGH

Archivo: `Atlas_Installer.bat`

Símbolo: completo (líneas 1-130)

Problema: El instalador rastreado en git es inconsistente con la documentación y los launchers:

1. Instala Python 3.11.8 (línea 28) pero `SETUP.md` y `README.md` recomiendan Python 3.13.
2. No crea `.venv` — instala dependencias con `pip install -r requirements.txt` en Python global (línea 89), contradiciendo `SETUP.md` que exige venv.
3. No crea `.env` ni copia `.env.example`.
4. No crea estructura de carpetas de `memory/Atlas_Memory/`.
5. No verifica ni instala Poppler ni FFmpeg (ambos requeridos por `pdf_reader.py` y `audio_transcriber.py`).
6. El acceso directo de UI (línea 106) lanza `streamlit run atlas_ui.py` sin `--server.port`, lo que usa el puerto por defecto 8501, inconsistente con `run_ui.bat` que usa 8401 para venv.
7. Descarga Tesseract desde URL de terceros (`digi.bib.uni-mannheim.de`) sin verificación de integridad.

Evidencia: `Atlas_Installer.bat:28` (`python-3.11.8-amd64.exe`), `:89` (`pip install` sin venv), `:106` (`streamlit run atlas_ui.py` sin puerto), `SETUP.md:26` (`py -3.13 -m venv .venv`), `run_ui.bat:41` (`--server.port 8401`).

Impacto: Un usuario que siga el instalador obtiene un setup distinto al documentado, con Python incorrecto, sin aislamiento, sin configuración, sin estructura de memoria, y con puertos inconsistentes. No reproducible.

Corrección mínima: Alinear instalador con `SETUP.md` (Python 3.13, venv, `.env.example` → `.env`, estructura de memoria, puertos) o eliminarlo y documentar setup manual.

Prueba de aceptación: Ejecutar instalador en VM limpia y verificar que `python -m core.system doctor --profile ui` reporta `ready_to_start=True`.

Estado: CONFIRMED BY CODE INSPECTION

### HIGH — Scripts de distribución incompletos (H-02)

Severidad: HIGH

Archivo: `scripts/crear_distribucion.py`, `scripts/limpiar_para_distribuir.py`

Símbolo: `crear_distribucion()`, `limpiar_atlas()`

Problema: El generador de distribución:

1. Hace `os.chdir(raiz_atlas)` (línea 26), mutando el CWD del proceso — frágil si se invoca desde otro script.
2. Crea `Atlas_Clean/` en el CWD actual (no en temp), riesgo de colisión.
3. El ZIP resultante se nombra `Atlas_v4_{timestamp}.zip` (línea 86) — versión v4, no v4.1.
4. `limpiar_para_distribuir.py` copia `core`, `agents`, `run.py`, `atlas_chat.py`, `atlas_ui.py`, `requirements.txt` pero omite `main_api.py`, `run.bat`, `run_ui.bat`, `Atlas_Installer.bat`, `.env.example`, `SETUP.md`, `docs/`, `tests/`, `scripts/`.
5. Crea `Perfil_Usuario.md` genérico pero el código productivo (`core/brain.py:50`, `core/memory_manager.py:13`) referencia `Perfil_Charly.md` — la distribución limpia no funcionaría sin renombrar.

Evidencia: `crear_distribucion.py:26` (`os.chdir`), `:86` (`Atlas_v4_`), `limpiar_para_distribuir.py:33-43` (lista incompleta), `:56` (`Perfil_Usuario.md` vs `Perfil_Charly.md` en `brain.py:50`).

Impacto: La distribución generada es incompleta y no funcional sin intervención manual. No reproducible.

Corrección mínima: Alinear lista de archivos con el repositorio funcional, corregir versión del ZIP a v4.1, resolver la inconsistencia `Perfil_Usuario.md`/`Perfil_Charly.md`, usar `TemporaryDirectory`.

Prueba de aceptación: Generar distribución, descomprimir en temp, crear venv, instalar requirements, ejecutar `python -m core.system doctor` — debe reportar ready.

Estado: CONFIRMED BY CODE INSPECTION

### MEDIUM — Rutas hardcodeadas de Poppler (M-01)

Severidad: MEDIUM

Archivo: `core/pdf_reader.py:36-58`

Símbolo: `_detectar_poppler()`

Problema: La detección de Poppler incluye rutas hardcodeadas específicas de la máquina del desarrollador (`C:\Tools\poppler\poppler-26.02.0\Library\bin`, `C:\Tools\poppler\poppler-24.08.0\Library\bin`). El fallback de emergencia (línea 54) es `C:\Tools\poppler\poppler-26.02.0\Library\bin` — ruta personal.

Evidencia: `pdf_reader.py:37-46` lista 9 rutas, varias con `C:\Tools\poppler\poppler-XX.XX.0`.

Impacto: En otra PC sin Poppler en esas rutas exactas, OCR de PDFs falla silenciosamente (retorna `None` y el logger warning). Degradación poco clara.

Corrección mínima: Priorizar `POPPLER_PATH` de `.env` y `shutil.which("pdftoppm")`; mantener rutas comunes solo como último recurso; documentar instalación de Poppler.

Prueba de aceptación: En PC sin Poppler en `C:\Tools`, con `POPPLER_PATH` seteado, OCR funciona.

Estado: CONFIRMED BY CODE INSPECTION

### MEDIUM — Log de seguridad en CWD (M-02)

Severidad: MEDIUM

Archivo: `core/security.py:20`

Símbolo: `_LOG_PATH = "atlas_security.log"`

Problema: El log de seguridad se escribe en `atlas_security.log` relativo al CWD, no en `paths.logs_dir`. Inconsistente con `operational_log.py` que sí usa `paths.logs_dir`.

Evidencia: `security.py:20` (`_LOG_PATH = "atlas_security.log"`), `paths.py:79` (`logs_dir = data_dir / "logs"`).

Impacto: En instalación empaquetada, el log quedaría en el CWD del lanzador (posiblemente Program Files, sin permisos de escritura).

Corrección mínima: Usar `paths.logs_dir / "atlas_security.log"`.

Prueba de aceptación: Lanzar Atlas con `ATLAS_DATA_DIR` en temp y verificar que el log se crea allí.

Estado: CONFIRMED BY CODE INSPECTION

### MEDIUM — Ausencia de lockfile reproducible (M-03)

Severidad: MEDIUM

Archivo: `requirements.txt`

Problema: No existe lockfile reproducible. `requirements.txt` usa rangos (`>=X,<Y`) sin versiones pinneadas. No hay `pip-tools`, ni `poetry.lock`, ni `uv.lock`.

Evidencia: `git ls-files | findstr lock` → vacío. `requirements.txt` usa 28 rangos de versiones.

Impacto: Una instalación en otra PC puede resolver versiones distintas de las probadas, especialmente para paquetes con componentes nativos (`chromadb`, `sentence-transformers`, `torch`, `pyaudio`, `pygame`). Riesgo de instalación no reproducible.

Corrección mínima: Generar un lockfile reproducible desde un entorno limpio mediante una herramienta reproducible como `pip-tools` (`pip-compile`) o `uv` (`uv lock`). `pip freeze` puede usarse únicamente como snapshot inicial para inspección, no como solución final garantizada, porque captura el estado de un entorno existente sin resolver dependencias de forma determinista desde un entorno limpio.

Prueba de aceptación: Instalar desde lockfile generado por `pip-compile` o `uv lock` en un venv limpio y ejecutar la suite de tests con el mismo resultado.

Estado: CONFIRMED BY CODE INSPECTION

### MEDIUM — Embeddings y Vosk sin pre-descarga ni verificación (M-04)

Severidad: MEDIUM

Archivo: `core/vector_store.py:42-44`, `core/speech_input.py:12,36`

Símbolo: `SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")`, `VOSK_MODEL_URL`

Problema: El modelo de embeddings (~120MB) y el modelo Vosk (~40MB) se descargan automáticamente al primer uso (lazy loading). No hay verificación previa, ni cache pre-empaquetado, ni mensaje claro de "descargando X MB" en el flujo de first-run.

Evidencia: `vector_store.py:42-44` (sin pre-descarga), `speech_input.py:36` (`urllib.request.urlretrieve`).

Impacto: First-run en PC sin internet o con conexión lenta falla o cuelga sin explicación clara. No reproducible offline.

Corrección mínima: Doctor debe detectar si el modelo de embeddings está cacheado; healer puede pre-descargarlo con consentimiento; documentar requisito de internet en first-run.

Prueba de aceptación: Doctor reporta `embeddings_model_cached: false` cuando no existe en cache.

Estado: CONFIRMED BY CODE INSPECTION

### LOW — Restauración lista variables obsoletas (L-01)

Severidad: LOW

Archivo: `scripts/restaurar_atlas.py:78`

Problema: El script de restauración menciona `BINANCE_API_KEY` y `BINANCE_API_SECRET` que no están en `.env.example` (que usa `NVIDIA_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`). Inconsistencia documental.

Evidencia: `restaurar_atlas.py:78-79` vs `.env.example:17-19`.

Corrección mínima: Alinear variables listadas con `.env.example`.

Estado: CONFIRMED BY CODE INSPECTION

### LOW — ZIP de distribución con versión v4 (L-02)

Severidad: LOW

Archivo: `scripts/crear_distribucion.py:86`

Problema: El ZIP se nombra `Atlas_v4_{timestamp}.zip` — versión v4, no v4.1.

Corrección mínima: `Atlas_v4.1_{timestamp}.zip` o derivar de `core.config.VERSION`.

Estado: CONFIRMED BY CODE INSPECTION

### LOW — Self-awareness usa os.getcwd() (L-03)

Severidad: LOW

Archivo: `core/self_awareness.py:130`

Símbolo: `"directorio_actual": os.getcwd()`

Problema: El reporte de auto-conocimiento usa `os.getcwd()` en lugar de `paths.project_root`.

Corrección mínima: Usar `paths.project_root` o `Path(__file__).resolve().parents[2]`.

Estado: CONFIRMED BY CODE INSPECTION

## 11. Claims confirmados

| Claim previo | Clasificación | Evidencia |
|---|---|---|
| 1. Dependencia de Python y `.venv` | CONFIRMED | `run.bat`, `run_ui.bat` prefieren `.venv`; `SETUP.md` exige venv; `Atlas_Installer.bat` no crea venv |
| 2. Dependencias Python pesadas/frágiles | CONFIRMED | `chromadb`, `sentence-transformers`, `torch`, `pyaudio`, `pygame` en `requirements.txt`; sin lockfile |
| 3. Rutas relativas dependientes del CWD | CONFIRMED | 60 coincidencias de `memory/Atlas_Memory` en código productivo; `CHROMA_PATH = "./vector_db"` |
| 4. Rutas hardcodeadas de máquina concreta | CONFIRMED | `pdf_reader.py:37-54` (`C:\Tools\poppler\...`) |
| 5. Almacenamiento en ubicaciones inestables | CONFIRMED | `security.py:20` (`atlas_security.log` en CWD); datos en CWD |
| 6. Dependencia externa de Ollama | CONFIRMED | `doctor.py` detecta Ollama; `healer` puede iniciarlo; sin Ollama, `local_llm` false |
| 7. Dependencia de Tesseract, Poppler, FFmpeg | CONFIRMED | `doctor.py:247-258` detecta externos; `pdf_reader.py`, `audio_transcriber.py` los requieren |
| 8. Descarga de embeddings en primer uso | CONFIRMED | `vector_store.py:42-44` lazy loading; `speech_input.py:36` descarga Vosk |
| 9. Ausencia de lockfile reproducible | CONFIRMED | `git ls-files | findstr lock` → vacío |
| 10. Configuración manual mediante `.env` | CONFIRMED | `.env.example` existe; `healer.fix_config` crea mínimo solo si falta; sin asistente |
| 11. Scripts de distribución incompletos | CONFIRMED | `limpiar_para_distribuir.py` omite `main_api.py`, launchers, `.env.example`, `docs/`, `tests/` |
| 12. Referencia a instalador inexistente | FALSE POSITIVE | `Atlas_Installer.bat` SÍ existe y está rastreado en git |
| 13. Puertos o launchers inconsistentes | CONFIRMED | `Atlas_Installer.bat:106` lanza Streamlit sin puerto (8501); `run_ui.bat` usa 8401/8501 con contrato documentado |
| 14. Ausencia de prueba en PC/VM limpia | NOT VERIFIED | No hay evidencia documental ni artefacto de validación en PC limpia |
| 15. Afirmaciones multiplataforma vs Windows | PARTIAL | `README.md` menciona Windows; `doctor.py` detecta OS; `paths.py` usa `LOCALAPPDATA`/`APPDATA` (Windows); pero `pdf_reader.py:50` incluye ruta Linux de Tesseract |

## 12. Claims parciales

- Portabilidad multiplataforma: `paths.py` y `doctor.py` son agnósticos, pero `pdf_reader.py` incluye rutas Linux y `Atlas_Installer.bat` es solo Windows. Atlas está diseñado para Windows pero no se afirma explícitamente "Windows-only".

## 13. Claims no verificados

- Instalación en Windows limpio: No hay evidencia de validación real en VM/PC limpia. `NOT VERIFIED`.
- Ejecución sin Python global: `run.bat`/`run_ui.bat` tienen fallback a `py`/global; no probado sin venv.
- Ejecución sin Ollama: Doctor marca `local_llm: false` pero `cloud_llm` puede funcionar; no probado end-to-end.
- Ejecución sin Internet: First-run requiere descargar embeddings y posiblemente Vosk; no probado offline.
- Instalación en ruta con espacios: `paths.py` usa `Path.resolve()` (robusto), pero código productivo usa strings relativos; no probado.
- Usuario sin permisos admin: `Atlas_Installer.bat` recomienda admin pero no lo exige; no probado.

## 14. Falsos positivos descartados

- Referencia a instalador inexistente (claim 12): `Atlas_Installer.bat` SÍ existe y está rastreado en git. El problema no es la inexistencia sino la inconsistencia y baja calidad del instalador existente.

## 15. Mapa de riesgos

| Riesgo | Severidad | Probabilidad | Bloquea instalación |
|---|---|---|---|
| Rutas relativas no conectadas a `paths.py` | HIGH | Alta | Sí |
| Instalador inconsistente con docs | HIGH | Alta | Sí |
| Distribución incompleta | HIGH | Alta | Sí |
| Sin lockfile | MEDIUM | Media | Parcial |
| Poppler rutas hardcodeadas | MEDIUM | Media | Parcial (solo OCR) |
| Log en CWD | MEDIUM | Media | Parcial (permisos) |
| Embeddings sin pre-descarga | MEDIUM | Media | Parcial (offline) |

## 16. Deuda técnica candidata

- `ATLAS-TD-014` (OPEN): Identidad interna `Perfil_Charly.md` acoplada — afecta distribución limpia.
- Nueva deuda: desconexión `paths.py` ↔ código productivo.
- Nueva deuda: instalador inconsistente.
- Nueva deuda: scripts de distribución incompletos y con versión v4.
- Nueva deuda: ausencia de lockfile reproducible.

## 17. Próximos cortes candidatos

| # | Corte candidato | Dependencia | Impacto |
|---|---|---|---|
| 1 | Conectar `paths.py` al código productivo — reemplazar constantes relativas en `config.py`, `vector_store.py`, `brain.py`, `memory_manager.py`, `chat_manager.py`, `security.py`, etc. por rutas derivadas de `get_paths()`. Mantener modo `development` por defecto. El planner deberá dividir esta migración en cortes pequeños según los consumidores y contratos reales de cada módulo. | Ninguna | Desbloquea todo lo demás |
| 2 | Alinear `Atlas_Installer.bat` con `SETUP.md` — Python 3.13, venv, `.env.example`→`.env`, estructura de memoria, puertos 8401, o eliminarlo y documentar setup manual. | Corte 1 (parcial) | Instalador funcional |
| 3 | Reparar scripts de distribución — lista completa de archivos, versión v4.1, `TemporaryDirectory`, resolver `Perfil_Usuario.md`/`Perfil_Charly.md`. | Corte 1 | Distribución reproducible |
| 4 | Generar lockfile reproducible — usar `pip-tools` (`pip-compile`) o `uv` (`uv lock`) desde un entorno limpio. `pip freeze` puede usarse como snapshot inicial para inspección, no como solución final garantizada. | Ninguna | Instalación determinista |
| 5 | Pre-descarga y verificación de embeddings — Doctor detecta cache; Healer pre-descarga con consentimiento; mensaje claro en first-run. | Ninguna | First-run offline |
| 6 | Limpiar rutas hardcodeadas de Poppler — priorizar `POPPLER_PATH` y `shutil.which`; documentar instalación. | Ninguna | OCR portable |
| 7 | Mover logs a `paths.logs_dir` — `security.py` y otros logs a `logs/`. | Corte 1 | Permisos correctos |
| 8 | Validación en VM limpia — documento de prueba de aceptación en Windows 10/11 limpio con y sin Ollama. | Cortes 1-7 | Evidencia de reproducibilidad |

## 18. Limitaciones

- No se ejecutó Atlas end-to-end (solo tests de sistema).
- No se validó en PC/VM limpia.
- No se inspeccionaron datos privados.
- No se probó empaquetado real (PyInstaller no configurado).
- HEAD real (`c842d66`) difiere del esperado (`9caf3af`) por 1 commit de refactor opencode; no afecta el alcance de portabilidad.

## 19. Estado final del working tree

Limpio al iniciar la auditoría. Limpio tras la ejecución de tests. El reporte documental se escribe sin `git add`, commit ni push.

## 20. Conclusión

Clasificación por dimensiones de portabilidad:

- PORTABLE PARA DESARROLLADOR: PASS
- EMPAQUETABLE: PARTIAL
- INSTALABLE: FAIL
- REPRODUCIBLE: FAIL
- ACTUALIZABLE: NOT VERIFIED
- RECUPERABLE: PARTIAL
- VALIDADO EN PC LIMPIA: NOT VERIFIED

Atlas es portable para desarrollador con setup manual siguiendo `SETUP.md`, pero no es instalable ni reproducible de forma automática hoy. El bloqueador central es que la política de rutas `core/system/paths.py` existe y está probada pero no está conectada al código productivo, que sigue dependiendo del CWD. El instalador existente y los scripts de distribución son inconsistentes con la documentación y generan artefactos incompletos. Sin un lockfile reproducible, la instalación de dependencias no es determinista. El camino a instalación reproducible requiere conectar `paths.py` primero (dividiendo la migración en cortes pequeños según consumidores y contratos reales), luego alinear instalador y distribución, generar lockfile con una herramienta reproducible, y finalmente validar en VM limpia.
