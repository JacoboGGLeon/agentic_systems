# Mejoras de aprendizaje · 2.1.4.dev8

Conservar los pilares de ejecución de 2.1.1/2.1.2 y una gramática de composición
sobre LangGraph. La revisión confía en compile, con Graph como nombre único y sin aliases históricos.

1. Mostrar la construcción real en cada tutorial/example: capacidades, datos,
   unidades, grafo y comprobaciones relevantes, con funciones locales legibles.
2. Usar Pydantic para estados y contratos de ejecución. Explicar errores antes
   de efectos, campos opcionales y salidas parciales, sin crear un modelo base propio.
3. Enseñar runtime y scheduler como controles de ejecución; separar su alcance
   de las aristas del grafo, policy, contract y plazo raíz compartidos.
4. Usar status/ok/data/human_results en el primer recorrido; reservar evidencia
   completa para depuración/auditoría. No confundir pausa con terminación.
5. Mantener una página de estado que distinga fuente, artefacto y evidencia.
6. Ejecutar notebooks en kernels nuevos y ejemplos contra wheel no editable;
   mantener negativos y fallos. Ejecutar online solo rutas y presupuesto autorizados.
7. Probar comprensión con usuarios nuevos. Esta revisión técnica no mide todavía
   tiempo de aprendizaje ni éxito sin ayuda.

[Recorrido recomendado](LEARNING_PATH_214.md) · [Inventario](NOTEBOOK_INVENTORY_214.md) ·
[Validación](LEARNING_VALIDATION_214.md) · [Estado](STATUS_214.md).
