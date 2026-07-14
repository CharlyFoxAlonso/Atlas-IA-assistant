# Jerarquía de fuentes de Atlas Auditor

## Propósito

Esta jerarquía resuelve contradicciones sobre el comportamiento esperado del producto. La fuente de mayor nivel prevalece sobre las inferiores.

## Orden de autoridad

1. **Constitución de Atlas Auditor**  
   Principios que ninguna decisión o implementación puede contradecir.

2. **Documentación de producto aprobada**  
   Visión, MVP y alcance vigente de Atlas Auditor.

3. **Decisiones arquitectónicas aceptadas**  
   ADR de Atlas Auditor que registren decisiones concretas y sus consecuencias.

4. **Especificaciones y criterios de aceptación aprobados**  
   Comportamientos verificables acordados para una entrega.

5. **Pruebas automatizadas vigentes**  
   Evidencia ejecutable del comportamiento esperado, siempre que no contradiga una fuente superior.

6. **Código de Atlas Auditor**  
   Describe el comportamiento implementado, que puede contener defectos o estar incompleto.

7. **Documentación heredada de Atlas Personal**  
   Referencia histórica y técnica reutilizable. No define por sí sola el producto Auditor.

8. **Comportamiento histórico, comentarios y supuestos**  
   Sirven como contexto, pero necesitan validación antes de convertirse en requisitos.

## Reglas de uso

- Una contradicción no se resuelve silenciosamente: se registra y se consulta la fuente superior.
- Que el código haga algo no significa que ese comportamiento sea correcto.
- Que Atlas Personal tenga una función no implica que Atlas Auditor deba conservarla.
- Una propuesta RFC no tiene autoridad de decisión hasta ser aceptada.
- Si ninguna fuente resuelve una duda, el estado correcto es pendiente de decisión.

## Jerarquía de evidencia dentro de una auditoría

La autoridad documental del producto no determina automáticamente la confiabilidad de la evidencia auditada. Para cada auditoría deben registrarse por separado:

1. la fuente original;
2. su procedencia e integridad conocidas;
3. las transformaciones aplicadas;
4. los criterios de evaluación;
5. las inferencias generadas.

Una inferencia nunca reemplaza a su fuente original.
