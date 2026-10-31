# Cierre de producto previo al PR · 2.1.4

Auditoría inicial dev7 conservada como antecedente. El avance implementado en
dev8 y su evidencia están en [el estado vigente](STATUS_214.md) y
[el informe dev8](../revisions/2.1.4/grammar-dev8/REPORT.md).

Estado al 29 de octubre de 2026: auditoría y criterios de cierre; **no es una
declaración de aceptación ni un congelamiento**. No se modificó el SDK ni se
incorporó ADA. La gramática de esta rama sigue siendo 2.1.4.dev7.

## Hallazgos verificables

| Prioridad | Hallazgo | Cierre necesario |
|---|---|---|
| Bloqueante | quality.yml instala el wheel 2.1.3 y espera esa versión. | Verificar el artefacto de la candidata actual. Un workflow verde sobre 2.1.3 no certifica dev7. |
| Bloqueante | quality.yml referencia examples/catalog_tools.py, ausente del árbol actual. | Sustituir esa puerta por una validación vigente del catálogo y probar el workflow completo. |
| Bloqueante | release-candidate.yml todavía ejecuta prepare_release_213.py. | Preparar la candidata y su manifiesto desde la versión/fuente actuales, preservando artefactos históricos. |
| Bloqueante | pytest por defecto y test_offline_214.py seleccionan solo tests/v214_graph. | Una suite canónica por contratos compartida por fuente, wheel y CI. La colección comprobada hoy tiene 120 casos, no 364. |
| Alta | tests/README.md describía 469 pruebas y cobertura de una API anterior. | Documento corregido: el JUnit dev7 contiene 120 + 44 + 167 + 20 + 13 = 364. El runner aún debe unificarse. |
| Alta | cli.py describe la API como 2.1.3 y un error de framework recomienda StateGraph. | Corregir mensajes/docstrings, añadir controles pertinentes y reconstruir/probar los bytes. El SDK no se cambió en esta auditoría. |
| Alta | Los ZIP didácticos preceden al notebook ampliado y a las correcciones de examples. | Regenerar entregables y manifiestos después del cierre editorial y verificar correspondencia con el SDK. |

[Hallazgos y hashes históricos](../revisions/2.1.4/pre-freeze-audit/01/findings.json) ·
[Colección por defecto](../revisions/2.1.4/pre-freeze-audit/01/default-collection.txt).

## Definición de terminado para las siete superficies

| Superficie | Narrativa y didáctica | Funcionalidad y API |
|---|---|---|
| source | Nombres/docstrings coherentes; comentarios explican decisiones, invariantes y efectos. Dividir funciones por responsabilidad sin ocultar el trabajo tras capas innecesarias. | Exportaciones/firmas verificadas; imports opcionales perezosos; errores y evidencia conservados. Revisar dependencias antes de declararlas prescindibles. |
| examples | Declarar las piezas relevantes, input → proceso → output concreto, negativos y límites visibles. Identificar los lanzadores. | Ejecutar entrypoints/notebooks con el wheel instalado y registrar perfil/hash. Distinguir configuración, fixture Python, servicio local y modelo real. |
| tutorials | Una ruta progresiva y una forma principal por concepto. Cuerpos de funciones visibles, sin importar un experimento entero para ocultar la composición. | Kernel limpio, orden completo y datos reproducibles. Cada elemento público conecta con lección y prueba de contrato. |
| API | Referencia canónica e inventario generado de firmas/métodos/parámetros. Opciones avanzadas después del recorrido básico. | Input/output, proyecciones, Pydantic, compile/run/arun, pausa y errores coherentes. Declarar la parte soportada de LangGraph y rechazar lo no integrado. |
| documentation | README, INSTALL, API, arquitectura, skill, changelog y estado cuentan el mismo producto. | Enlaces y fragmentos comprobados. Historia identificada; sin transferir evidencia de otros bytes ni porcentajes heredados. |
| CLI | version/api/doctor/new con ayuda clara. doctor distingue SDK instalado de credenciales o servicio probado. | Códigos de salida, JSON, errores, no sobrescritura y rutas con espacios. Ejecutar fuera del checkout y probar el proyecto generado con la misma API. |
| pytests | Organizar por responsabilidad de contrato; las regresiones explican el fallo que impiden. | Selección canónica compartida por fuente, wheel y CI. Medir cobertura actual; incluir negativos, efectos, concurrencia, Memory y publicación. |

Minimalismo no significa limitar artificialmente todos los archivos a dos imports:
Pydantic, stdlib, boto3 y los SDK deben usarse directamente cuando sean parte del
problema. Tampoco significa comprimir ramas en expresiones difíciles de explicar.
Los helpers tienen nombre, responsabilidad y cuerpo visible en la lección.

## Orden antes de congelar

1. Cerrar el alcance AWS/ADA: sesión reutilizable general frente a utilidades
   empresariales opcionales. La [propuesta ADA](ADA_214_PROPOSAL.md) no es API disponible.
2. Reconciliar source/API/CLI, pruebas y workflows. Corregir primero lo que pueda
   probar otro artefacto o una suite incompleta.
3. Completar el recorrido editorial de tutorials/examples y consolidar entradas
   equivalentes. Los nombres históricos no obligan a mantener otra gramática.
4. Ejecutar offline la suite canónica, notebooks, ejemplos, scaffolder y fragmentos
   documentales contra fuente y wheel instalado. Conservar todos los intentos.
5. Medir cobertura y revisar análisis estático, arquitectura, secretos, dependencias,
   metadatos e instalación mínima/opcional sobre esos bytes.
6. Revalidar online los proveedores disponibles con presupuesto autorizado. Fijar
   modelos/endpoints y conservar pendientes cuando no haya entorno. Quedan dos
   solicitudes de la campaña dev5: no alcanza para prometer un cierre live de la
   candidata. Esta auditoría no consumió inferencia.
7. Regenerar SDK/sdist y los entregables modificados de aprendizaje, Studio, skill
   y manifiestos; comprobar que código y documentación se corresponden.
8. Entonces congelar la candidata local y preparar el PR. Integración/publicación
   requerirán CI 3.10–3.14 correcta y los mismos bytes aprobados.

## Lo que no bloquea el alcance declarado

Persistencia durable de Memory/continuaciones, memoria vectorial, una API RL
completa, rollback general y Studio empresarial con wallet son capacidades
futuras. No deben añadirse deprisa para cerrar 2.1.4. Su ausencia debe explicarse
donde un usuario pueda inferir que existen.

La revisión previa de examples conserva 57 entrypoints correctos y siete
notebooks con perfil offline correcto, con una celda local de Studio omitida.
MCP/A2A tiene evidencia previa en un perfil separado. Es una base de validación;
no sustituye el cierre de las siete superficies anteriores.
