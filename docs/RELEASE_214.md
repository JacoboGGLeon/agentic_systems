# Cierre de 2.1.4

La revisión actual es 2.1.4.dev8, local y sin publicar.
[Informe de pruebas](../revisions/2.1.4/grammar-dev8/REPORT.md).

Antes de un release estable: congelar bytes y dependencias, ejecutar CI con
Python 3.10–3.14, autorizar campaña live, resolver casos obligatorios y repetir
las rutas acordadas con ese mismo wheel no editable. Conservar fallos y
consumo; un cambio de bytes invalida la aceptación anterior.

Las pruebas offline de Tools, grafos, Context/Memory, scheduler y pausa no
sustituyen pruebas con un LM real. GPU/vLLM, AWS IAM y ADA IAM mantienen su
estado pendiente. Los protocolos locales se informan aparte de inferencia.

La publicación requerirá el flujo de TestPyPI → PyPI/GitHub y hashes idénticos
de los artefactos aprobados. Esta tarea no la autoriza ni la ejecuta.
