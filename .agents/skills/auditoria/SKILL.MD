---

name: auditoria
description: Audita integralmente el proyecto antes de implementar cambios. Úsala para revisar arquitectura, conexiones entre módulos, errores, código incompleto, seguridad, privacidad, rendimiento, mantenibilidad y preparación para producción. No modifica archivos salvo autorización explícita.
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Auditoría integral del proyecto

Realiza primero una auditoría de solo lectura. No modifiques ningún archivo durante esta etapa.

## Objetivo

Determinar el estado real del proyecto, detectar problemas y proponer un plan seguro y priorizado para continuar su desarrollo.

## Procedimiento

1. Lee primero `AGENTS.md` y la documentación existente del repositorio.
2. Identifica el lenguaje, framework, arquitectura, puntos de entrada y comandos disponibles.
3. Genera un mapa resumido de:

   * carpetas principales;
   * módulos y responsabilidades;
   * flujo de datos;
   * dependencias entre componentes;
   * servicios externos;
   * almacenamiento local o remoto;
   * permisos y datos sensibles.
4. Busca:

   * archivos huérfanos o código muerto;
   * imports, rutas o referencias rotas;
   * funcionalidades simuladas, incompletas o desconectadas;
   * errores silenciosos y manejo deficiente de excepciones;
   * duplicación de lógica;
   * inconsistencias de tipos, contratos o estados;
   * riesgos de seguridad y privacidad;
   * problemas de rendimiento;
   * configuraciones inseguras;
   * secretos o credenciales expuestos;
   * pruebas faltantes o insuficientes.
5. Ejecuta únicamente comprobaciones seguras y no destructivas disponibles en el proyecto, como análisis estático, compilación, lint y tests.
6. No supongas que una función está correctamente conectada solo porque el proyecto compila.
7. Distingue claramente entre:

   * hechos verificados;
   * indicios;
   * hipótesis que requieren validación.

## Formato del informe

Entrega el resultado en este orden:

### 1. Resumen ejecutivo

Estado general del proyecto en lenguaje claro.

### 2. Mapa de arquitectura

Componentes principales y cómo se conectan.

### 3. Hallazgos críticos

Problemas que impiden publicar, ejecutar o usar correctamente el producto.

### 4. Hallazgos importantes

Problemas que pueden causar errores, deuda técnica o dificultades futuras.

### 5. Mejoras recomendadas

Optimizaciones que no son bloqueantes.

### 6. Evidencias

Para cada hallazgo, indica:

* archivo;
* ruta;
* símbolo o función;
* explicación;
* impacto;
* nivel de confianza.

### 7. Plan de acción

Propón fases pequeñas y verificables, ordenadas por prioridad, riesgo y dependencia.

## Reglas

* No cambies código durante la auditoría.
* No borres ni reemplaces archivos.
* No instales dependencias sin autorización.
* No expongas secretos encontrados; informa solamente su ubicación y tipo.
* No presentes con certeza algo que no haya sido comprobado.
* Si el repositorio es demasiado grande, comienza con un inventario general y propone una auditoría por módulos.
* Antes de implementar correcciones, solicita autorización y presenta la lista exacta de archivos que se modificarían.
