# Crawler web seguro de Atlas

**Estado:** Implementado  
**Módulo:** `core/web_crawler.py`  
**Interfaz actual:** pestaña “Rastreo Inteligente” de Streamlit

## Propósito

El crawler recorre páginas HTML de un único origen, descubre enlaces, filtra contenido por tema, organiza el material, lo digiere con el motor elegido por el usuario y actualiza el índice semántico una vez al finalizar.

No es un navegador general, un descargador de archivos ni una herramienta para explorar redes internas.

## Flujo

```text
URL inicial
   │
   ├─ validación de esquema, host, DNS e IP
   ├─ validación de robots.txt
   └─ cola acotada por solicitudes y profundidad
          │
          ├─ redirección manual y mismo origen
          ├─ tipo y tamaño de respuesta
          ├─ extracción de texto y enlaces
          ├─ filtro temático
          ├─ nombre y ruta seguros
          ├─ digestión con motor/modelo seleccionado
          └─ archivo Markdown con hash de URL
                    │
                    └─ reindexación única al terminar
```

## Límites predeterminados

| Límite | Valor |
|---|---:|
| Páginas guardadas | 20, configurable entre 1 y 100 |
| Solicitudes | 10 por página objetivo |
| Profundidad | 3 |
| Cola | 500 URLs |
| Respuesta individual | 5 MiB |
| Redirecciones | 5 |
| Espera entre solicitudes | 0,5 segundos |
| Timeout | 5 segundos de conexión, 15 de lectura |

`max_pages` representa páginas guardadas. `max_requests` limita de manera independiente todas las páginas intentadas, incluidas las irrelevantes y fallidas.

## Seguridad de red

- Solo se aceptan HTTP y HTTPS.
- Se rechazan credenciales embebidas en URL.
- El host debe resolver exclusivamente a direcciones públicas globales.
- Se bloquean loopback, redes privadas, link-local y direcciones reservadas.
- Las redirecciones son manuales y se validan antes de seguirlas.
- Todos los enlaces deben mantener esquema, host y puerto del origen inicial.
- Se rechazan extensiones binarias conocidas.
- Solo se procesan HTML, XHTML y texto plano.
- La respuesta se lee en streaming y se corta si supera el límite real.

### Riesgo residual: DNS rebinding

La validación DNS ocurre antes de que la biblioteca HTTP establezca la conexión. Un servidor DNS hostil podría responder con una IP pública durante la comprobación y con una privada durante la conexión. La mitigación completa requerirá un adaptador HTTP que conecte contra la IP validada preservando SNI y Host, o un proxy local con política de egreso.

Hasta implementar esa capa, el crawler debe tratarse como apropiado para sitios públicos conocidos y no como aislamiento de red de nivel empresarial.

## Seguridad de archivos

- La raíz debe permanecer dentro de `memory/Atlas_Memory`.
- Cada carpeta y archivo final vuelve a validarse.
- Los nombres generados se normalizan a ASCII seguro.
- Se rechazan implícitamente nombres vacíos y reservados de Windows.
- Cada archivo incorpora un hash SHA-256 corto de la URL normalizada.
- Variantes por query generan archivos distintos.

## Privacidad y modelos

El crawler utiliza el motor y modelo seleccionados en “Motor de Digestión”:

- `atlas`: procesamiento local mediante Ollama;
- `prometeo`: NVIDIA;
- `groq`: Groq Cloud.

El mismo motor se utiliza para relevancia, categorización y digestión. Elegir un proveedor de nube implica enviarle fragmentos de las páginas rastreadas.

Si el clasificador falla, la página no se guarda. Esta política cerrada evita ingerir contenido no verificado por un fallo transitorio del proveedor.

## Descubrimiento y almacenamiento

Los enlaces se descubren aunque la página actual sea corta o no sea relevante. Esto permite atravesar portadas e índices sin guardar su contenido.

Una página guardada todavía no se anuncia como “indexada”. Primero se archiva. Al finalizar el lote, Atlas reconstruye el índice una sola vez y reporta por separado si esa operación tuvo éxito.

## Pruebas

Las pruebas usan sesiones HTTP, DNS, LLM y digestores simulados. No acceden a Internet.

Escenarios cubiertos:

- localhost, IP privada y protocolos inválidos;
- credenciales en URL;
- destino fuera de memoria;
- redirección hacia una red privada;
- respuesta sobredimensionada;
- descubrimiento mediante una página irrelevante;
- propagación del motor y modelo;
- límite independiente de solicitudes;
- colisiones de query;
- enlaces externos.

## Trabajo futuro

- Mitigación completa de DNS rebinding.
- Cancelación desde Streamlit.
- Progreso separado de visitadas, omitidas y guardadas.
- Caché HTTP y reanudación.
- Backoff específico para HTTP 429 y 503.
- Política configurable de robots y crawl-delay.
- Índice incremental para evitar reconstrucciones completas.

