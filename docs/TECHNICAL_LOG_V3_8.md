# 📓 Bitácora de Desarrollo Técnico: Atlas AI System
**Estado Actual:** Versión 3.8  
**Responsable:** Desarrollo Core / AI Engineering  
**Fecha de última actualización:** 09 de Julio de 2026

---

## 1. Resumen Ejecutivo
Atlas es un sistema de asistencia de IA híbrido diseñado para balancear la privacidad absoluta (modelos locales vía Ollama) con la potencia de procesamiento masivo (APIs de NVIDIA y Groq). El sistema implementa una arquitectura de RAG (Retrieval-Augmented Generation) semántico y un sistema de agentes especializados.

---

## 2. Cronología de Evolución y Cambios

### 🟢 Fase de Estabilidad y Corrección (v3.6 $\rightarrow$ v3.7)
**Objetivo:** Solucionar errores críticos de conectividad y hardcoding de modelos.

#### 🛠️ Problemas Detectados:
- **Error 404 en Groq:** El sistema intentaba llamar a modelos de NVIDIA (`meta/llama-3.1-70b-instruct`) utilizando el motor de Groq, lo que resultaba en errores de "Modelo no encontrado".
- **Hardcoding de Modelos:** Los identificadores de los modelos estaban dispersos en el código en lugar de estar centralizados.
- **Inconsistencia en el Digestor:** El motor de ingesta de documentos no permitía la selección dinámica de modelos para Groq.

#### ✅ Soluciones Implementadas:
1. **Centralización de Configuración:** Se movieron todos los defaults de modelos a `core/config.py`, creando `MODELO_GROQ_DEFAULT` y `MODELOS_GROQ_DISPONIBLES`.
2. **Refactorización de `core/brain.py`:** Se modificó la función `pensar_con_streaming` para aceptar el parámetro `modelo_groq` de forma independiente, eliminando la dependencia cruzada con los modelos de NVIDIA.
3. **Actualización de Interfaz (UI):** Se implementaron selectores dinámicos en `atlas_ui.py` para que el usuario pueda elegir el modelo exacto según el motor activo (Atlas, Prometeo o Groq).
4. **Sincronización de la API:** Se ajustó `main_api.py` para transmitir los parámetros de modelo correctos al cerebro del sistema.

---

### 🔵 Fase de Expansión de Capacidades (v3.7 $\rightarrow$ v3.8)
**Objetivo:** Aumentar la versatilidad de entrada de datos y proporcionar herramientas de benchmarking.

#### 🛠️ Implementaciones Nuevas:
1. **Soporte para EPUB y HTML:**
   - **Por qué:** Los usuarios necesitaban procesar libros electrónicos y capturas de páginas web sin depender de conversiones externas.
   - **Cómo:** Se integraron las librerías `ebooklib` y `BeautifulSoup4` en `core/universal_loader.py`, implementando una limpieza de etiquetas HTML/CSS para extraer solo el texto relevante.
   - **Impacto:** El RAG ahora puede indexar bibliotecas enteras de libros digitales y documentación web.

2. **Prompt Playground (Laboratorio de Pruebas):**
   - **Por qué:** En un sistema multi-modelo, es crítico saber qué cerebro responde mejor a un prompt específico antes de desplegarlo en el chat principal.
   - **Cómo:** Se creó la función `pensar_sin_streaming` en `core/brain.py` y una interfaz comparativa en `atlas_ui.py` que renderiza las respuestas de Local, Prometeo y Groq lado a lado.
   - **Impacto:** Optimización del flujo de trabajo del usuario y validación rápida de la calidad de las respuestas.

---

## 3. Análisis de Avances y Retrocesos

### 📈 Avances Significativos
- **Interoperabilidad Total:** El sistema ahora es agnosticamente compatible con tres motores de inferencia distintos sin conflictos de configuración.
- **Soberanía de Datos:** Se ha perfeccionado el flujo de "Digestión Local", asegurando que archivos sensibles nunca salgan de la máquina del usuario.
- **Modularidad:** La separación entre el `universal_loader` y el `digestion_worker` permite añadir nuevos formatos de archivo sin romper la lógica de indexación.

### 📉 Retrocesos y Desafíos
- **Sincronización de Versiones:** Se detectó que múltiples archivos mantenían referencias a versiones antiguas (v3.4), lo que generaba confusión en la documentación técnica. (Solucionado en v3.8 mediante auditoría global).
- **Gestión de Memoria en Streaming:** Se identificaron cuellos de botella al procesar respuestas muy largas en modo comparativo. (Solucionado mediante la implementación de `pensar_sin_streaming`).

---

## 4. Estado Técnico Final (v3.8)

| Componente | Estado | Tecnología Principal |
| :--- | :--- | :--- |
| **Motores** | ✅ Operativo | Ollama / NVIDIA NIM / Groq Cloud |
| **RAG** | ✅ Optimizado | ChromaDB / SentenceTransformers |
| **Ingesta** | ✅ Expandida | PDF, DOCX, PPTX, EPUB, HTML, OCR |
| **UI** | ✅ Avanzada | Streamlit / Multi-Session JSON |
| **API** | ✅ Estable | FastAPI / Streaming Response |

---

## 5. Guía de Mantenimiento para Futuros Desarrolladores
Para añadir un nuevo modelo:
1. Registrar el ID del modelo en `core/config.py` dentro de la lista correspondiente.
2. Verificar que el motor seleccionado tenga la API Key configurada en el `.env`.
3. Reiniciar la aplicación para refrescar el estado de la sesión de Streamlit.
