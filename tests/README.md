# Pruebas · 2.1.4.dev8

La suite canónica tiene **469 casos correctos**, sin fallos ni omisiones, en
Python 3.14.2. Se ejecuta contra fuente y contra una instalación no editable
fuera del checkout. CI prepara la misma suite para Python 3.10–3.14; su ejecución
remota todavía está pendiente.

| Área | Casos | Responsabilidad |
|---|---:|---|
| tests/v214_graph | 120 | Graph, Context, episodios, pausa y RunResult |
| tests/grammar214 | 44 | Tools Pydantic, contratos y Eval aislada |
| tests/learning214 | 169 | Negocio, controles, ejemplos y configuración |
| tests/release/test_release_publication.py | 20 | Identidad, conflictos y publicación |
| Studio seleccionado | 13 | Controlador y widgets, sin certificar toda la UI |
| tests/current | 103 | Sesión AWS, compilador, errores, linaje, CLI y contratos |

[JUnit instalado](../revisions/2.1.4/grammar-dev8/installed-suite-closure.xml) ·
[Cobertura](../revisions/2.1.4/grammar-dev8/installed-coverage-closure.json) ·
[Informe](../revisions/2.1.4/grammar-dev8/REPORT.md).

## Ejecución

`pyproject.toml` declara testpaths; runner y CI usan el mismo perfil. La suite
histórica permanece fuera de esta selección vigente.

```console
python -m pytest --collect-only -q
python scripts/test_offline_214.py --source
python scripts/test_offline_214.py
```

El último comando exige el wheel instalado y no usa src mediante pythonpath.
El runner bloquea conexiones de aplicación y subprocesos. Jupyter y MCP/A2A
tienen perfiles locales separados. No se ejecutan proveedores LM.

La cobertura de sentencias medida es 100%, sin bajar el umbral existente.
La política excluye motor privado y plantillas; no es cobertura de toda la
distribución ni de ramas. Se comprueban errores, intentos, consumo, serialización,
Context, Memory aislada, plazos compartidos y efectos.
