# Subsistema operativo de Atlas

**Estado:** Implementado, primera versión estable  
**Alcance:** `core/system`  
**Plataforma principal inicial:** Windows 11

## Propósito

`core/system` concentra el diagnóstico, la reparación controlada y el arranque de Atlas. Su objetivo es permitir que la aplicación funcione en equipos incompletos, se degrade de forma comprensible cuando falten capacidades opcionales y pueda integrarse posteriormente con un launcher gráfico, un runtime privado y un instalador.

Este subsistema no implementa lógica de inteligencia artificial, RAG, memoria, agentes ni interfaz de usuario.

## Componentes

| Módulo | Responsabilidad | Puede modificar el sistema |
|---|---|---:|
| `paths.py` | Calcular rutas de desarrollo y aplicación empaquetada | No |
| `result_types.py` | Definir contratos serializables | No |
| `command_runner.py` | Ejecutar procesos sin `shell=True` y devolver resultados estructurados | Solo por solicitud del consumidor |
| `operational_log.py` | Registrar acciones reales en JSONL rotativo y redactado | Crea logs únicamente para operaciones reales |
| `doctor.py` | Inspeccionar el equipo, dependencias, capacidades y, de forma opt-in, consistencia del índice | No |
| `healer.py` | Aplicar reparaciones explícitas, idempotentes y clasificadas por riesgo; proyectar IDX-C3 de forma segura | Sí |
| `launcher.py` | Coordinar diagnóstico, reparaciones autorizadas y arranque | Puede iniciar Atlas |
| `__main__.py` | Exponer la CLI técnica segura | Solo con `--apply` |

## Flujo principal

```text
CLI, futura UI o instalador
          │
          ▼
       Doctor
          │
          ├── listo ───────────────► Launcher ─► Atlas
          │
          └── no listo
                 │
                 ▼
        Healer autorizado
                 │
                 ▼
          nuevo diagnóstico
                 │
                 └───────────────► Launcher ─► Atlas
```

Doctor nunca llama a Healer. Healer consulta Doctor para su flujo general, pero no
decide por sí mismo qué debe repararse. La ruta controlada `index_consistency` es la
excepción explícita: recibe `diagnosis={}` y usa el proveedor read-only de estado del
índice para evitar un Doctor general innecesario. Launcher solo delega reparaciones
seguras expresamente autorizadas y no contiene lógica de instalación.

## Contratos

Los resultados se implementan como `dataclass` y ofrecen `to_dict()`:

- `CheckResult`: resultado de una comprobación individual.
- `DiagnosisResult`: estado general, preparación y capacidades.
- `RepairResult`: resultado de una reparación.
- `LaunchResult`: resultado de un intento de arranque.
- `CommandResult`: resultado de un proceso.
- `DownloadResult`: contrato reservado para la futura capa de descargas.

Todos los contratos deben seguir siendo serializables mediante `json.dumps()`.

## Severidades y preparación

Doctor clasifica las comprobaciones como:

- `critical`: impide iniciar el producto objetivo.
- `recommended`: permite iniciar con degradación o menor robustez.
- `optional`: habilita una función adicional.

`health_score` es un indicador informativo. No determina por sí solo si Atlas puede arrancar. La decisión se expresa mediante `ready_to_start` y `critical_issues`.

Doctor publica perfiles independientes en `startup_profiles`:

- `ui`: Streamlit y dependencias comunes;
- `cli`: terminal interactiva y dependencias comunes;
- `api`: FastAPI, Uvicorn y dependencias comunes.

El perfil predeterminado es `ui` para conservar compatibilidad. Launcher solicita automáticamente el perfil correspondiente a su destino.

GPU NVIDIA, Git y claves de proveedores concretos no son requisitos universales. Atlas necesita al menos un backend de IA funcional, local o remoto.

## Capacidades y modo degradado

Doctor deriva capacidades a partir de cadenas completas de dependencias. Por ejemplo, PDF OCR necesita el paquete de conversión, Tesseract y Poppler; encontrar solamente uno no alcanza.

Entre las capacidades informadas se encuentran:

- LLM local.
- NVIDIA, Groq u OpenAI en la nube.
- RAG semántico.
- extracción de texto PDF y OCR.
- transcripción de audio.
- entrada y salida de voz, en línea y fuera de línea.
- visión.
- búsqueda web.

La UI debe consumir este mapa para ocultar, deshabilitar o explicar funciones degradadas. No debe volver a implementar detecciones.

## Política de rutas

En desarrollo se preserva el diseño existente:

```text
Atlas/
├── memory/Atlas_Memory
├── vector_db
├── cache
└── logs
```

En una aplicación empaquetada se separan programa y datos:

```text
carpeta de aplicación/
└── código y puntos de entrada

%LOCALAPPDATA%/Atlas/
├── memory
├── vector_db
├── cache
├── logs
├── downloads
├── temp
├── bin
└── models

%APPDATA%/Atlas/
└── configuración
```

`ATLAS_DATA_DIR` selecciona la raíz general de datos y, por defecto, también la raíz
de memoria; de ella derivan Chroma, caché, logs y demás datos locales.
`ATLAS_MEMORY_DIR` reemplaza únicamente la ubicación de los documentos fuente y no
reubica Chroma ni el manifiesto. El subsistema todavía no mueve datos existentes.

## Seguridad

- Doctor es estrictamente de solo lectura.
- Healer comienza con `dry_run=True`.
- Las reparaciones reales requieren `--apply` desde la CLI.
- `index_consistency` es un componente controlado: no pertenece a
  `SAFE_COMPONENTS`, no participa de `fix_all` y Launcher no puede seleccionarlo como
  reparación automática.
- Paquetes y modelos requieren además `--allow-heavy`.
- No se usa `shell=True`.
- Los argumentos de procesos son listas.
- No se registran valores de claves API.
- `.env` existente nunca se sobrescribe.
- No se escriben placeholders que puedan parecer credenciales válidas.
- No se instala en Python global.
- Los fallos se aíslan por componente.
- Launcher no instala paquetes ni descarga modelos.
- Las acciones reales de Healer y Launcher generan eventos JSONL rotativos en `logs/atlas-system.log`.
- Los eventos incluyen timestamp UTC e identificador, pero redactan campos sensibles.

## Integración con una interfaz gráfica

Una UI puede importar las APIs públicas directamente:

```python
from core.system import Healer, Launcher, diagnosticar_sistema
from core.index_status import consultar_estado_indice
```

No debe lanzar `python -m core.system` mediante un subproceso. La CLI y la UI son adaptadores distintos sobre las mismas APIs.

Integración recomendada:

1. Mostrar `diagnosticar_sistema()` en una sección “Estado del sistema”.
2. Presentar salud, preparación, capacidades y rutas sin valores secretos.
3. Consultar el estado del índice solo por acción explícita; no hacerlo al importar,
   renderizar ni en cada rerun.
4. Para el índice, construir `Healer(diagnosis={}, dry_run=True)` para el preview y
   repetir con `dry_run=False` únicamente después de una confirmación clara. No usar
   `Healer()` genérico en esa ruta porque dispararía Doctor.
5. Tratar `busy`, `blocked`, resultados parciales, fallos y
   `still_inconsistent` como no exitosos. La proyección presenta ordinales, no
   identidades documentales ni muestras de huérfanos.
6. Mantener instalaciones pesadas y elevación de privilegios fuera de la UI hasta
   disponer de un bootstrapper confiable.

Estas reglas aplican a la futura NiceGUI. La UI debe importar los contratos Python
existentes, no invocar la CLI como subproceso, y no duplicar diagnóstico,
clasificación, lock ni reparación. No autorizan una API o factory nueva.

## Reparación controlada del índice

La CLI técnica actual separa consulta y consentimiento:

```powershell
python -m core.system heal index_consistency
python -m core.system heal index_consistency --apply
```

El primer comando es un preview read-only y no adquiere el writer lock. El segundo
autoriza a Healer a delegar en `reparar_indice()`, que aplica el lock fail-fast y el
post-check de IDX-C3. Un preview `INCONSISTENT` planificado devuelve `0`; un preview
`DEGRADED` o `UNAVAILABLE` bloqueado devuelve `1`; un error de argumentos devuelve
`2`; una aplicación no exitosa devuelve `3`. Doctor, `!indexar status`, Streamlit y
el arranque permanecen read-only o no ejecutan esta reparación.

## Cómo agregar una comprobación

1. Implementar una función privada y sin efectos secundarios en `doctor.py`.
2. Devolver valores serializables y estados diferenciados.
3. Incorporar el resultado a `checks` o `capabilities`.
4. Clasificar su severidad según el producto mínimo, no según conveniencia de desarrollo.
5. Agregar pruebas con mocks para ausencia, fallo y funcionamiento.

## Cómo agregar una reparación

1. Definir un componente acotado en `healer.py`.
2. Clasificar el riesgo como seguro, moderado o pesado.
3. Implementar primero el resultado de simulación.
4. Exigir consentimiento cuando corresponda.
5. Hacer la acción idempotente.
6. Volver a diagnosticar después de un cambio real.
7. Aislar errores y no borrar datos.
8. Exponerla en la CLI solamente si su contrato está probado.

## Decisiones pendientes

- Estrategia reversible de migración de memoria privada.
- Runtime privado definitivo y formato de distribución.
- Política de descargas HTTPS, fuentes permitidas y SHA-256.
- Detección específica por perfil de arranque UI/CLI.
- Normalización de Unicode en consolas Windows capturadas.
- Migración posterior a NiceGUI conservando las fronteras read-only y de
  consentimiento existentes.
- Rotación y retención de logs operativos.
