> Suite histórica de la gramática anterior. La revisión actual 2.1.4.dev2 se valida en tests/v214_graph; no ofrece compatibilidad con estos constructores anteriores.

# Regresiones 2.1.4.dev1

El cierre actual ejecuta 278 pruebas entre tests/v213 y tests/v214, sobre un
wheel no editable, con guard offline que bloquea red e inferencia.

Esta carpeta cubre Context, Memory, contratos, estado y fuentes de episodios,
grafo común, separación actor/orquestador, pausa/reanudación, límites y
conservación de evidencia. Las fixtures de transporte no certifican modelos.
Los resultados OpenAI reales y su presupuesto están separados en revisions/2.1.4/.

```powershell
$env:PYTHONPATH=(Resolve-Path .tmp/candidate214-dev1/site-packages).Path
.tmp/implementation213-runtime/Scripts/python.exe scripts/test_offline_214.py
```

`--source` sirve durante desarrollo; el cierre usa el wheel instalado.
