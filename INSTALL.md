# Instalación · Agentic Systems 2.1.3

Python 3.10–3.14. Crea y activa un entorno virtual para tu proyecto:

```bash
python -m venv .venv
python -m pip install agentic-systems==2.1.3
agentic-systems version
agentic-systems doctor
agentic-systems new my_project
```

En Windows activa con `.venv\Scripts\Activate.ps1`; en macOS/Linux usa
`source .venv/bin/activate`. Selecciona ese mismo intérprete como kernel de Jupyter.

Para todos los proveedores y frameworks probados aquí:

```bash
python -m pip install "agentic-systems[openai,bedrock,langgraph,openai-agents,strands]==2.1.3" jupyter
```

Los extras son `openai`, `bedrock`, `langgraph`, `openai-agents`, `strands`,
`vllm`, `vllm-client`, `vllm-server`, `dev` y `all`. `all` excluye el servidor
vLLM GPU, que necesita un entorno preparado. No existe el extra `[ada]`.
Instalar dependencias no inicia servidores ni valida un modelo.

## Variables para los tutorials de proveedores

Configúralas en el entorno del proceso que inicia Jupyter. Los notebooks leen
`os.environ`; no cargan claves desde archivos del repositorio ni las imprimen.
Si ya tienes `.env`, puedes cargarlo en tu sesión antes de iniciar Jupyter.
Studio sí dispone de su propio cargador de `.env`.

| Ruta | Variables |
|---|---|
| Python | Ninguna |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL_ID`; `OPENAI_BASE_URL` opcional |
| Ollama | `OLLAMA_API_KEY`, `OLLAMA_MODEL_ID`, `OLLAMA_BASE_URL` |
| Bedrock API key | `AWS_BEARER_TOKEN_BEDROCK`, `BEDROCK_MODEL_ID`, `AWS_REGION`; `BEDROCK_BASE_URL` opcional |

Para Ollama local sin autenticación puedes usar un valor no secreto en
`OLLAMA_API_KEY`; el endpoint y modelo deben corresponder a tu servidor.
No cambies de modelo para convertir un fallo en un éxito sin registrar el cambio.
AWS IAM y ADA IAM tienen preparación y aceptación separadas, todavía pendientes.

## Studio

1. Descarga [Studio 2.1.3](https://github.com/JacoboGGLeon/agentic_systems/releases/download/v2.1.3/agentic-systems-studio-2.1.3-final-local.zip).
2. Descomprímelo y entra en la carpeta que contiene `wheels/`.
3. Instala el wheel de Studio y abre la interfaz:

```bash
python -m pip install "./wheels/agentic_systems_studio-2.1.3-py3-none-any.whl[ui,frameworks,notebook]"
```

```python
from agentic_systems_studio import launch_studio
session = launch_studio()
```

Python funciona sin credenciales. Consulta [Studio](examples/agentic_systems_studio/README.md)
para el uso desde notebook y sus laboratorios. El ZIP contiene el SDK y la aplicación;
no contiene claves ni todas las dependencias para una instalación desconectada.

## Artefactos y validación

El [release](https://github.com/JacoboGGLeon/agentic_systems/releases/tag/v2.1.3)
publica hashes y evidencia del SDK, sdist, Studio y notebook aprobado. Para una
instalación desconectada, prepara además un wheelhouse con sus dependencias y usa
`--no-index --find-links`. Los tests se ejecutan contra el wheel instalado, sin
modo editable; no se considera el checkout como evidencia del paquete instalado.

[Tutorials](tutorials/README.md) · [Examples](examples/README.md) ·
[API](docs/API_213.md) · [Resultados actuales](docs/LEARNING_VALIDATION_213.md)
