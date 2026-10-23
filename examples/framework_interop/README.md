# Cuatro frameworks en un System

```python
from examples.framework_interop.example import run

report = run()
```

**Input:** value=42 y un historial vacío. **Proceso:** native, LangGraph,
OpenAI Agents y Strands ejecutan su Tool por turno, incrementan el valor y
registran su identidad. **Output:** value=46 y las cuatro identidades en orden.
El System exterior usa un StateGraph real; Eval comprueba la versión Python.

La [declaración compartida](../agentic_systems_studio/src/agentic_systems_studio/lab/interop.py)
es la misma que utiliza Studio. Cada etapa pasa el dato observado en su Tool;
la prosa del modelo queda como presentación. Se exige una llamada exacta y se
rechaza que el modelo altere los argumentos o invente resultados.

`run()` utiliza Python Runtime con los cuatro SDK reales. La campaña también
ejecuta una asignación mixta: native/Python, LangGraph/OpenAI, OpenAI Agents/Ollama
y Strands/Bedrock. No hay sustitución de proveedores.

Studio permite ejecutar además checkpoint/resume, handoffs/guardrails/sesión y
MCP/A2A. Son capacidades nativas de sus SDKs conectadas en la frontera de
framework, no otros constructores de Agentic Systems.

[Resultados e intentos](../../revisions/2.1.3/framework-evidence/REPORT.md).
El runner técnico de campañas vive aquí para mantenimiento; no forma parte
del recorrido de uso del example.
