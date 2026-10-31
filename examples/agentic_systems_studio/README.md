# Agentic Systems Studio · 2.1.4

Studio es una aplicación separada del SDK. Instala el wheel local 2.1.4 y luego
`python -m pip install "./examples/agentic_systems_studio[ui,notebook]"`.
Abre [el notebook](notebooks/01_studio.ipynb) o inicia la interfaz:

```bash
python -m streamlit run examples/agentic_systems_studio/src/agentic_systems_studio/ui.py
```

```python
from agentic_systems_studio import ConversationConfig, build_conversational_system
app = build_conversational_system(ConversationConfig(provider='python-runtime', framework='native'))
result = app.run('Hola')
assert result.ok
print(result.data)
```

El controlador usa Graph de LangGraph; native, openai-agents y strands son actores.
El estado interno de cada nodo lleva una envoltura payload de negocio, no
árboles de resultados. El resultado público conserva answer, historial,
validación, eventos y linaje. Las claves quedan fuera del estado.

Las pruebas separan controlador/conversación, UI, handoffs y MCP/A2A. Los
servicios locales usan fixtures sin LM; la integración con actores LM se prueba
aparte. [Matriz, evidencia y pendientes](../../docs/LEARNING_VALIDATION_214.md).

Para inferencia configura las variables de entorno y AGENTIC_BUDGET_FILE con
un contador persistente autorizado. La prueba de Python no acredita calidad de
conversación de un modelo ni todos los controles de la interfaz.

[La demostración explícita](example.py) muestra una conversación mínima con
StateGraph, Tools, Skills, Agent, System, Context y Memory. La API de aplicación
del controlador completo que aparece arriba es una integración adicional, no
el reemplazo de esas declaraciones. El notebook muestra ambas fronteras.

[Validación histórica dev5](../../revisions/2.1.4/contracts-dev5/REPORT.md).
La evidencia de revisiones anteriores permanece histórica.

El chat Python del controlador completo usa un fixture hello_world determinista;
no interpreta lenguaje ni selecciona automáticamente la calculadora. La Tool
safe_calculate puede ejecutarse explícitamente. Las pruebas online del controlador
con LMs sí verifican historial y llamada a calculadora; no cubren todos los controles UI.
