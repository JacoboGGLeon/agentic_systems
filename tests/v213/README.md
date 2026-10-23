# Contratos 2.1.3

Esta es la suite vigente seleccionada por pyproject. Las otras suites del
repositorio describen la API anterior y no son compatibilidad soportada.

Usar scripts/test_offline_213.py contra el wheel instalado. --source es solo
desarrollo local; la aceptación se vincula al wheel no editable. La suite usa
un guard offline, cuatro frameworks con Python Runtime y fixtures explícitas
para modelos/HTTP/procesos; no ejecuta inferencia real.
