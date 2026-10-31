# Instalación local · 2.1.4.dev7

Revisión de trabajo sin publicar. Instala el wheel nuevo en un entorno limpio,
sin modo editable. Los resultados live de dev5 no certifican este artefacto.
Desde el checkout, con sus dependencias disponibles:

```bash
python -m pip install "revisions/2.1.4/grammar-dev7/builds/01/agentic_systems-2.1.4.dev7-py3-none-any.whl[openai,bedrock,openai-agents,strands]"
python -m pip install "./examples/agentic_systems_studio[ui,notebook]"
python -m pip install jupyterlab ipykernel
```

```python
import pydantic
import agentic_systems as toolkit
assert toolkit.__version__ == "2.1.4.dev7"
```

El SDK y CLI van en el wheel. Tutorials/examples, Studio y la skill se
entregan aparte. Selecciona el kernel del entorno donde instalaste el wheel.
Python determinista no requiere credenciales. La validación offline omite
celdas live y servicios locales expresamente.

```bash
agentic-systems new mi_proyecto
cd mi_proyecto
python app.py
```

[Artefacto y validación](revisions/2.1.4/grammar-dev7/REPORT.md).
Se conservan intactos los wheels y resultados dev5. Ninguna publicación ni
inferencia adicional está autorizada para esta revisión. vLLM/GPU, IAM y ADA
siguen pendientes de su propia validación.
