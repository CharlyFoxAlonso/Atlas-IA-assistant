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
| `doctor.py` | Inspeccionar el equipo, dependencias y capacidades | No |
| `healer.py` | Aplicar reparaciones explícitas, idempotentes y clasificadas por riesgo | Sí |
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

Doctor nunca llama a Healer. Healer consulta Doctor, pero no decide por sí mismo qué debe repararse. Launcher solo delega reparaciones seguras expresamente autorizadas y no contiene lógica de instalación.

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

`ATLAS_DATA_DIR` y `ATLAS_MEMORY_DIR` permiten seleccionar ubicaciones explícitas. El subsistema todavía no mueve la memoria existente.

## Seguridad

- Doctor es estrictamente de solo lectura.
- Healer comienza con `dry_run=True`.
- Las reparaciones reales requieren `--apply` desde la CLI.
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
```

No debe lanzar `python -m core.system` mediante un subproceso. La CLI y la UI son adaptadores distintos sobre las mismas APIs.

Integración recomendada:

1. Mostrar `diagnosticar_sistema()` en una sección “Estado del sistema”.
2. Presentar salud, preparación, capacidades y rutas sin valores secretos.
3. Ofrecer simulación de reparaciones seguras.
4. Pedir confirmación clara antes de llamar a Healer con `dry_run=False`.
5. Mantener instalaciones pesadas y elevación de privilegios fuera de la UI de Streamlit hasta disponer de un bootstrapper confiable.

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
- Integración visual del diagnóstico en Streamlit.
- Rotación y retención de logs operativos.
