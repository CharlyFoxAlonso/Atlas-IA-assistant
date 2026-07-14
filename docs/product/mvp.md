# MVP de Atlas Auditor

## Objetivo

Demostrar que Atlas Auditor puede recibir un conjunto controlado de evidencia, evaluarlo con criterios explícitos y producir un resultado trazable sin modificar las fuentes.

## Flujo mínimo

1. El usuario selecciona o proporciona la evidencia que desea auditar.
2. Atlas Auditor registra la procedencia de cada elemento.
3. El usuario selecciona o define los criterios de evaluación.
4. Atlas Auditor ejecuta la evaluación.
5. El resultado separa observaciones, inferencias, contradicciones y datos faltantes.
6. Cada hallazgo referencia su evidencia y criterio.

## Capacidades incluidas

- operar únicamente sobre datos de prueba aislados;
- aceptar al menos un formato documental ya soportado por la base heredada;
- conservar las fuentes sin modificaciones;
- producir un informe legible de auditoría;
- indicar el estado de cada hallazgo;
- mostrar límites y errores sin ocultarlos;
- permitir que el usuario revise el resultado.

## Fuera del MVP

- acceso automático a la memoria de Atlas Personal;
- modificación o corrección automática de documentos auditados;
- auditorías autónomas sin criterios definidos;
- decisiones finales sin revisión humana;
- migración masiva de datos;
- integraciones externas que no sean necesarias para validar el flujo;
- reorganización completa de la documentación heredada.

## Criterios de aceptación

El MVP se considera demostrado cuando un caso de prueba puede ejecutarse de principio a fin y:

- ninguna fuente original resulta modificada;
- todos los hallazgos identifican evidencia y criterio;
- hechos e inferencias aparecen diferenciados;
- los datos insuficientes se reportan como tales;
- otra persona puede comprender cómo se obtuvo el resultado;
- el flujo no depende de datos privados de Atlas Personal.
