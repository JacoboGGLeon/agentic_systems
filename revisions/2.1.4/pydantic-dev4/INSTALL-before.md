# Instalación local · 2.1.4.dev3

Esta revisión no está publicada. Desde la raíz del checkout instala el wheel
local exacto, sus extras y la aplicación Studio separada:

```bash
python -m venv .venv-user
# Activar el entorno según tu sistema.
python -m pip install "revisions/2.1.4/json-markdown-fix/candidate/agentic_systems-2.1.4.dev3-py3-none-any.whl[openai,bedrock,openai-agents,strands]"
python -m pip install ./examples/agentic_systems_studio
python -m pip install jupyterlab ipykernel
python -m ipykernel install --user --name agentic-dev3
python -m jupyterlab
```

Selecciona ese kernel. Los notebooks y ejemplos son archivos del checkout;
`pip install agentic-systems` desde PyPI no instala este desarrollo ni Studio.
Instala `examples/agentic_systems_studio[ui,notebook]` para la interfaz/widgets.

También se preparó el [wheel local de Studio](revisions/2.1.4/learning-dev3/candidate/agentic_systems_studio-2.1.4.dev3-py3-none-any.whl),
instalado y comprobado sin modo editable. Sus fuentes coinciden con este checkout.
La [skill portable para ChatGPT](revisions/2.1.4/learning-dev3/candidate/agentic-systems-skill-2.1.4.dev3.zip)
contiene SKILL.md y sus recursos; está preparada para cargarla, no instalada
automáticamente en tu cuenta de ChatGPT. La instalación personal de Codex sí
se actualizó y se conservó su respaldo.

```python
import agentic_systems as toolkit
assert toolkit.__version__ == '2.1.4.dev3'
```

Para Python no hacen falta claves. Los proveedores usan variables de entorno:
OPENAI_API_KEY y OPENAI_MODEL; AWS_BEARER_TOKEN_BEDROCK, BEDROCK_MODEL_ID y
AWS_REGION; OLLAMA_API_KEY, OLLAMA_MODEL y OLLAMA_BASE_URL. GPU local usa el
endpoint explícito de su notebook. Nunca pegues claves en notebooks o Context.

Qwen Cloud requiere que el catálogo del servicio lo ofrezca; no se sustituye
por Gemma. vLLM necesita preparar Linux/WSL y GPU antes de probarlo:
[guía](docs/VLLM_GPU_214.md). API-key Bedrock no certifica IAM ni ADA.

```bash
agentic-systems new mi_proyecto
cd mi_proyecto
python app.py
```

El scaffolder genera fuente, recursos, notebook y manifiesto. La skill dev3
agrega además un test de contrato. Generar no es validar: ejecuta la aplicación
y sus aserciones contra el mismo wheel. [Tutorials](tutorials/README.md).
