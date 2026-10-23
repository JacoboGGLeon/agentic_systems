# Studio

Conversa con un proveedor y framework explícitos, ejecuta Tools y consulta
RunResult y lineage. La misma aplicación sirve desde Python, notebook e interfaz.

## Instala y abre

Descarga [Studio 2.1.3](https://github.com/JacoboGGLeon/agentic_systems/releases/download/v2.1.3/agentic-systems-studio-2.1.3-final-local.zip),
descomprímelo y entra en la carpeta que contiene `wheels/`:

```bash
python -m pip install "./wheels/agentic_systems_studio-2.1.3-py3-none-any.whl[ui,frameworks,notebook]"
```

```python
from agentic_systems_studio import launch_studio

session = launch_studio()
```

Abre el enlace que devuelve la función. En notebook presenta un botón; Colab
usa su proxy. Para terminar, `session.server.stop()`. También puedes seguir
[el notebook de Studio](notebooks/01_studio.ipynb).

Studio se distribuye por separado del SDK `agentic-systems==2.1.3`. El ZIP
incluye ambos wheels, fuentes, notebook y tests. Las dependencias se descargan
al instalarlo; el ZIP no es un wheelhouse desconectado.

## Desde Python

```python
from agentic_systems_studio import build_conversational_system

studio = build_conversational_system()
answer = studio.run("Hola")
answer.text
```

El inicio usa un mock determinista de Python sin credenciales ni inferencia.
Para un modelo externo, configura sus variables en el entorno o `.env` antes
de abrir Studio. Selecciona proveedor y framework en la interfaz. No hay fallback.
Las claves no se copian al código ni a los resultados.

```python
from agentic_systems_studio import ConversationConfig, build_conversational_system

studio = build_conversational_system(
    ConversationConfig(provider="openai-runtime", framework="langgraph")
)
answer = studio.run("Calcula 17 * 19 usando la calculadora.")
answer.text
```

Enviar este mensaje al modelo consume llamadas. La campaña de validación usa
un contador persistente autorizado; la aplicación distingue ese perfil de su
uso habitual. El cálculo se verifica mediante una Tool y su evento se conserva
en RunResult. El historial público está acotado; no equivale a memoria persistente
entre servidores nuevos.

## Explora las capacidades de cada framework

| Framework | Laboratorio disponible |
|---|---|
| native | Tools, contexto y coordinación mediante la API común |
| LangGraph | pausa, checkpoint y reanudación de una aprobación |
| OpenAI Agents | transferencia a especialista, guardrail y sesión |
| Strands | Tool MCP y agente A2A con servicios locales reales |
| Todos | cuatro actores en un System; Python o proveedores mixtos |

La [implementación](src/agentic_systems_studio/lab/) usa los SDKs nativos en las
opciones del framework y conserva el resultado de la API común. No añade
constructores alternativos a la librería.

[Validación actual](../../docs/LEARNING_VALIDATION_213.md) ·
[Evidencia original del release](../../revisions/2.1.3/closeout-evidence/REPORT.md) ·
[Instalación y variables](../../INSTALL.md)

Los resultados acreditan escenarios concretos. vLLM/GPU, AWS IAM y ADA IAM
requieren validación posterior; este Studio no es ADA Studio.
