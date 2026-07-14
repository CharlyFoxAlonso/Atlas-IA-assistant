---
name: auditoria
# process: metodología de auditoría transversal, no ligada a un módulo específico
type: process
description: |
  Audita un proyecto de software para detectar problemas de arquitectura, calidad,
  seguridad, rendimiento y mantenibilidad.
  Usar cuando el usuario solicite una revisión completa antes de implementar cambios.
  No usar cuando el usuario pida una modificación directa o desarrollo de funcionalidad nueva.
---

# Auditoría

## Propósito

Realizar una auditoría técnica completa del proyecto antes de implementar cualquier cambio. Identificar el estado real del código, detectar riesgos, inconsistencias, errores ocultos, deuda técnica y oportunidades de mejora.

Durante esta etapa no deben modificarse archivos. El objetivo es comprender completamente el proyecto antes de realizar cualquier implementación.

La auditoría debe ser objetiva, verificable y basada únicamente en evidencia encontrada dentro del repositorio.

## Cuándo usarla

- El usuario solicita una revisión completa antes de implementar cambios
- El usuario pide un diagnóstico de la salud del proyecto
- Se necesita identificar deuda técnica, riesgos o código muerto antes de una modificación mayor
- El equipo necesita una línea de base antes de una refactorización

## Cuándo no usarla

- El usuario pide una modificación directa sin revisión previa
- El cambio es menor y no justifica una auditoría completa
- Ya se realizó una auditoría reciente y no hubo cambios significativos

## Procedimiento

Sigue este orden de trabajo estrictamente.

### Fase 1 — Comprensión

Antes de analizar problemas:

- Identifica el lenguaje y el framework.
- Identifica la arquitectura general.
- Identifica los módulos principales.
- Identifica el punto de entrada de la aplicación.
- Identifica los servicios internos y externos.
- Identifica la estructura de carpetas.
- Comprende el flujo completo de la aplicación.

No realices conclusiones todavía.

---

### Fase 2 — Auditoría

Analiza cuidadosamente:

- Arquitectura
- Organización del proyecto
- Calidad del código
- Acoplamiento entre módulos
- Duplicación de lógica
- Código muerto
- Archivos sin uso
- Funciones sin utilizar
- Riesgos de seguridad
- Riesgos de privacidad
- Manejo de errores
- Rendimiento
- Escalabilidad
- Mantenibilidad
- Legibilidad
- Consistencia del estilo
- Posibles bugs
- Código incompleto
- Funcionalidades parcialmente implementadas

---

### Fase 3 — Evidencias

Cada problema encontrado debe incluir:

- Archivo
- Función
- Línea aproximada
- Explicación
- Impacto
- Nivel de severidad

No hagas afirmaciones sin evidencia.

---

### Fase 4 — Recomendaciones

Ordena las mejoras por prioridad:

1. Críticas
2. Altas
3. Medias
4. Bajas

Explica el beneficio esperado de cada una.

## Reglas

Durante una auditoría debes cumplir estrictamente estas reglas:

- No modificar ningún archivo.
- No crear archivos nuevos.
- No eliminar código.
- No instalar dependencias.
- No ejecutar comandos destructivos.
- No asumir que algo funciona porque compila.
- No asumir que una función está conectada porque existe.
- No inventar información cuando no haya evidencia.

Si encuentras incertidumbre, indícala explícitamente.

Si el proyecto es demasiado grande:

- Comienza realizando un inventario general.
- Divide el proyecto por módulos.
- Audita un módulo por vez.
- Mantén el contexto de cada módulo separado.

Antes de sugerir cambios:

- Explica el problema.
- Explica por qué ocurre.
- Explica las consecuencias.
- Propón una solución.
- Espera autorización antes de implementar modificaciones.

## Formato de salida

Toda auditoría debe entregarse siguiendo exactamente esta estructura.

# Resumen ejecutivo

Describe el estado general del proyecto en pocas líneas.

Indica si el proyecto se encuentra:

- Excelente
- Bueno
- Aceptable
- Riesgoso
- Crítico

Explica brevemente el motivo.

---

# Arquitectura detectada

Describe:

- Arquitectura utilizada
- Framework
- Lenguaje
- Módulos principales
- Flujo general
- Dependencias importantes

---

# Problemas críticos

Lista únicamente los problemas que pueden:

- impedir el funcionamiento
- producir pérdida de datos
- comprometer la seguridad
- romper la arquitectura
- impedir la publicación

Para cada uno indicar:

- Severidad
- Archivo
- Componente
- Descripción
- Evidencia
- Recomendación

---

# Problemas importantes

Lista los problemas que generan:

- deuda técnica
- mantenimiento difícil
- rendimiento deficiente
- código duplicado
- mala organización
- errores potenciales

---

# Mejoras recomendadas

Ordena las mejoras desde la más importante hasta la menos importante.

Para cada mejora indica:

- beneficio esperado
- complejidad
- riesgo
- prioridad

---

# Fortalezas encontradas

No solo informes errores.

Destaca también las decisiones de diseño acertadas y las buenas prácticas encontradas.

---

# Plan de acción

Construye una hoja de ruta dividida en fases.

Ejemplo:

Fase 1
- ...

Fase 2
- ...

Fase 3
- ...

Cada fase debe ser pequeña, verificable y segura.

---

# Conclusión

Resume el estado general del proyecto e indica cuál debería ser el siguiente paso recomendado antes de continuar el desarrollo.
