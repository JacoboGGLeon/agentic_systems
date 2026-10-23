# Agentic Systems

Construye agentes, coordínalos y comprueba sus resultados con una sola API.

```bash
python -m pip install agentic-systems==2.1.3
```

```python
import agentic_systems as toolkit

worker = toolkit.Agent("total", toolkit.Action("sum", lambda data: {"total": sum(data["values"])}))
result = worker.run({"values": [2, 3, 5]})
result.data  # {"total": 10}
```

Para coordinar agentes, conserva la misma forma de ejecutar:

```python
app = toolkit.System("application", toolkit.Sequence((worker,)))
app.run({"values": [2, 3, 5]}).data  # {"total": 10}
```

Agent organiza el trabajo de una unidad; System coordina unidades. Ambos usan
`Sequence`, `Parallel` o `Graph`, con funciones Python para decidir el siguiente
paso. `run()` devuelve un RunResult; `compile()` prepara esa misma declaración
sin ejecutar su trabajo. Tools implementan operaciones, Skills las agrupan,
Environment procesa episodios con memoria y Eval comprueba sus resultados.

## Aprende por necesidad

| Quiero… | Empiezo aquí |
|---|---|
| Entender Tools, Skills, Agent, System, Environment y Eval | [Tutorials: core](tutorials/core/00_start.ipynb) |
| Ejecutar Python, OpenAI, Ollama o Bedrock API key | [Tutorials: providers](tutorials/README.md#providers) |
| Usar LangGraph, handoffs de OpenAI Agents o MCP/A2A en Strands | [Tutorials: frameworks](tutorials/README.md#frameworks) |
| Consultar contratos, parámetros y RunResult | [Tutorials: API](tutorials/README.md#api) · [Referencia completa](docs/API_213_SURFACE.md) |
| Ver una aplicación completa | [Recorrido de API y pedidos](examples/api_walkthrough/01_api_user_guide.ipynb) |
| Reutilizar una implementación concreta | [49 examples y su alcance real](examples/README.md) |
| Conversar y explorar frameworks en una interfaz | [Studio](examples/agentic_systems_studio/README.md) |

Los tutoriales enseñan paso a paso. Los examples muestran aplicaciones y patrones.
En ambos se distingue **input → proceso → output** y se conserva la evidencia de
ejecución. Descarga o clona el repositorio para disponer de este material; el
paquete de PyPI instala el SDK y su CLI.

## Proveedores y frameworks

El proveedor elige dónde se ejecuta el modelo; el framework elige el loop del
Agent. Se configuran por separado y no hay sustituciones automáticas.

```bash
python -m pip install "agentic-systems[openai,bedrock,langgraph,openai-agents,strands]==2.1.3"
```

Python Runtime funciona sin claves ni inferencia. Para modelos externos,
configura sus variables de entorno según [la instalación](INSTALL.md) y abre
el tutorial del proveedor. Ejecutar sus celdas live consume llamadas.

## Abre Studio

Studio es una aplicación separada, incluida en
[el ZIP de Studio 2.1.3](https://github.com/JacoboGGLeon/agentic_systems/releases/download/v2.1.3/agentic-systems-studio-2.1.3-final-local.zip).
Descárgalo, descomprímelo e instala el wheel de `wheels/` con el extra `ui`.
La [guía de Studio](examples/agentic_systems_studio/README.md) incluye el comando
completo y un notebook para abrir la interfaz.

```python
from agentic_systems_studio import launch_studio

session = launch_studio()
```

Desde la interfaz puedes seleccionar proveedor y framework, conversar y consultar
los resultados. Python es el punto de partida determinista. Las capacidades de
checkpoint, handoff, MCP, A2A e interoperabilidad tienen escenarios específicos.

## Resultados que puedes inspeccionar

Cada ejecución conserva RunResult, eventos de Tools y linaje. Publicamos
[los resultados por example y notebook](docs/LEARNING_VALIDATION_213.md),
[el inventario de notebooks y gramática](docs/NOTEBOOK_INVENTORY_213.md) y
[la evidencia original del release](revisions/2.1.3/closeout-evidence/REPORT.md).
Un caso con entradas guardadas se identifica como tal; no equivale a una generación
live. El informe distingue las pruebas actuales de las históricas.

**2.1.3 está publicada** en [PyPI](https://pypi.org/project/agentic-systems/2.1.3/)
y [GitHub](https://github.com/JacoboGGLeon/agentic_systems/releases/tag/v2.1.3).
Los artefactos publicados y sus hashes permanecen inmutables. Este repositorio
puede mejorar su material didáctico después del release. vLLM/Colab GPU, AWS IAM y
ADA IAM siguen pendientes de ejecución en sus entornos. No se incluye el extra
`[ada]` ni un Studio empresarial.

[API](docs/API_213.md) · [Instalación](INSTALL.md) · [CLI](docs/CLI_213.md) ·
[Validación y desarrollo](docs/VALIDATION_213.md)
