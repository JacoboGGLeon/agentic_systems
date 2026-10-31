# InstalaciÃ³n local Â· 2.1.4.dev8

RevisiÃ³n de trabajo sin publicar. Instala el wheel nuevo en un entorno limpio,
sin modo editable. Los resultados live de dev5 no certifican este artefacto.
Desde el checkout, con sus dependencias disponibles:

```bash
python -m pip install "revisions/2.1.4/grammar-dev8/delivery-build07/dist/agentic_systems-2.1.4.dev8-py3-none-any.whl[openai,bedrock,openai-agents,strands]"
python -m pip install "revisions/2.1.4/grammar-dev8/delivery-build07/dist/agentic_systems_studio-2.1.4.dev8-py3-none-any.whl[ui,notebook]"
python -m pip install jupyterlab ipykernel
```

```python
import pydantic
import agentic_systems as toolkit
assert toolkit.__version__ == "2.1.4.dev8"
```

El SDK y CLI van en el wheel. Tutorials/examples, Studio y la skill se
entregan aparte. Selecciona el kernel del entorno donde instalaste el wheel.
Python determinista no requiere credenciales. La validaciÃ³n offline omite
celdas live y servicios locales expresamente.

```bash
agentic-systems new mi_proyecto
cd mi_proyecto
python app.py
```

[Artefacto y validaciÃ³n](revisions/2.1.4/grammar-dev8/REPORT.md).
Se conservan intactos los wheels y resultados dev5. Ninguna publicaciÃ³n ni
inferencia adicional estÃ¡ autorizada para esta revisiÃ³n. vLLM/GPU, IAM y ADA
siguen pendientes de su propia validaciÃ³n.

El diagnÃ³stico ADA es un paquete independiente. DespuÃ©s del SDK y boto3,
puedes instalar su wheel local dev8 o, desde el checkout:

```bash
python -m pip install --no-deps --no-build-isolation ./integrations/ada
agentic-systems-ada doctor
```

Esto no instala credenciales ni comprueba acceso a AWS. No hay un extra ada
duplicado de bedrock ni una segunda forma de construir Agents o Systems.
