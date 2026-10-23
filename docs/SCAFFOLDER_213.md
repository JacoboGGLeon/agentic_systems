# Scaffolder 2.1.3

El SDK raíz contiene la API. Los proyectos solo importan agentic_systems.

```text
src/agentic_systems/
  __init__.py          # 18 exports
  _grammar.py          # unidades, flujos, episodios, evaluación
  _tools.py            # operaciones y Skills
  _results.py          # resultado JSON único
  _configuration.py    # configuración y recursos
  _contracts.py        # contratos y adaptación privada del actor
  _engine/             # motores privados de proveedores/frameworks
  _scaffolding.py      # generación desde recursos instalados
  _templates/          # declaración única de pedidos y proyecto
  cli.py
tutorials/             # 19 notebooks organizados
  core/                # Tools, Skills, Agent/System, Environment, Eval y resultados
  providers/           # Python, OpenAI, Ollama, Bedrock API key y serving
  frameworks/          # LangGraph, OpenAI Agents, Strands e interoperabilidad
  api/                 # contratos, jueces, runtime y opciones
examples/              # aplicaciones, ejemplos focalizados e historia
tests/v213/            # contratos actuales
```

`agentic-systems new /ruta/nueva/proyecto` rechaza destinos existentes y crea:

```text
proyecto/
  app.py
  pyproject.toml
  .env.example
  README.md
  manifest.json
  SHA256SUMS.txt
  src/order_fulfillment/
    system.py
    tools.py
    skills.py
    settings.py
    verification.py
    offline.py
    fixtures/
  tests/test_contract.py
  notebooks/01_order_challenge.ipynb
  test_offline.py
  execute_notebook.py
  evidence/
```

```text
python app.py --both
python test_offline.py
python execute_notebook.py
```

La app, tests y notebook usan el mismo build_system. No se copia la librería
ni una fachada. La plantilla comienza con validation=not-run; generar archivos
no valida su ejecución. La evidencia del proyecto ejecutado se conserva aparte
del ZIP limpio y sus hashes. El ejemplo solo permite Python Runtime offline.
