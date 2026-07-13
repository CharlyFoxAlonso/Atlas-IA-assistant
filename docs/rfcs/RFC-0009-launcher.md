# RFC-0009: Coordinación de arranque mediante Launcher

**Estado:** Aceptado e implementado  
**Fecha:** 2026-07-13  
**Ámbito:** `core/system/launcher.py`

## Contexto

Atlas dispone de dos puntos de entrada históricos:

- `run.py` para la terminal interactiva;
- `atlas_ui.py` para Streamlit.

Los scripts `.bat` seleccionan intérpretes y puertos de forma diferente, no comparten diagnóstico y pueden recurrir al Python global. Se necesita una capa reutilizable por desarrollo, CLI, ejecutable e instalador.

## Decisión

Launcher coordina el siguiente flujo:

1. Ejecutar Doctor.
2. Delegar únicamente reparaciones seguras autorizadas.
3. Volver a diagnosticar después de cambios reales.
4. Verificar `ready_to_start`.
5. Verificar el punto de entrada.
6. Construir un comando con argumentos separados.
7. Simular o iniciar Atlas.
8. Devolver `LaunchResult`.

El destino predeterminado es la UI en el puerto 8401. También existe un perfil CLI.

## Límites

Launcher no debe:

- instalar paquetes;
- descargar modelos;
- modificar PATH;
- elevar privilegios;
- conocer procedimientos de instalación de Tesseract, Poppler o FFmpeg;
- implementar lógica de IA;
- duplicar el diagnóstico;
- ejecutar comandos arbitrarios;
- iniciar si Doctor informa problemas críticos.

## Reparaciones autorizables

Launcher acepta solamente componentes de `SAFE_COMPONENTS`. Las reparaciones pesadas son rechazadas incluso si el consumidor intenta incluirlas.

La autorización es explícita:

```python
Launcher(dry_run=True).launch(
    target="ui",
    authorized_repairs=["folders", "config"],
)
```

## Simulación

`dry_run=True` es el valor predeterminado. En ese modo Launcher:

- diagnostica;
- simula reparaciones;
- valida preparación y punto de entrada;
- devuelve el comando planificado;
- no inicia procesos.

La CLI exige `--apply` para construir un Launcher con `dry_run=False`.

## Integración con Streamlit

Streamlit no debe iniciar otra instancia de sí mismo mediante Launcher. Dentro de la UI, la integración correcta es:

- Doctor para mostrar estado y capacidades;
- Healer para simular o aplicar reparaciones seguras;
- no usar Launcher para “reiniciar” el mismo proceso sin un supervisor externo.

Launcher sí es apropiado para:

- un bootstrapper anterior a Streamlit;
- un ejecutable de escritorio;
- un servicio supervisor;
- la CLI técnica;
- el futuro instalador.

## Consecuencias

### Positivas

- Un único flujo de decisión para arranque.
- Separación entre diagnóstico, reparación y proceso.
- Compatibilidad con UI y CLI sin `shell=True`.
- Puerto predeterminado consistente.

### Limitaciones actuales

- La preparación se calcula globalmente y todavía no diferencia todos los requisitos por perfil UI/CLI.
- No se monitoriza la vida completa del proceso iniciado.
- No existe protocolo de reinicio supervisado.
- No se abre automáticamente el navegador.

## Trabajo futuro

- Perfiles de preparación específicos para UI, CLI y API.
- Supervisión, reinicio y captura estructurada de fallos tempranos.
- Integración con runtime privado.
- Comunicación de progreso con una interfaz gráfica nativa.
- Reemplazo gradual de `run.bat` y `run_ui.bat` después de validar compatibilidad.

