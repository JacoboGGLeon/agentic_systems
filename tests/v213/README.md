> Suite histórica de la gramática anterior. La revisión actual 2.1.4.dev2 se valida en tests/v214_graph; no ofrece compatibilidad con estos constructores anteriores.

# Contratos 2.1.3

> En esta rama las regresiones base se ejecutan también sobre 2.1.4.dev1, con expectativas actualizadas para contratos y estado de episodios. Los contratos históricos exactos de 2.1.3 permanecen en su tag publicado.

Esta es la suite vigente seleccionada por pyproject. Las otras suites del
repositorio describen la API anterior y no son compatibilidad soportada.

Usar scripts/test_offline_213.py contra el wheel instalado. --source es solo
desarrollo local; la aceptación se vincula al wheel no editable. La suite usa
un guard offline, cuatro frameworks con Python Runtime y fixtures explícitas
para modelos/HTTP/procesos; no ejecuta inferencia real.
