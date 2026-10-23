# Agentic Systems

Construye agentes, coordínalos y comprueba sus resultados con una sola API.

```python
import agentic_systems as toolkit

worker = toolkit.Agent("total", toolkit.Action("sum", lambda data: {"total": sum(data["values"])}))
result = worker.run({"values": [2, 3, 5]})
result.data  # {"total": 10}
```

Para coordinar unidades, conserva la misma forma de ejecutar:

```python
app = toolkit.System("application", toolkit.Sequence((worker,)))
app.run({"values": [2, 3, 5]}).data
```

Agent y System admiten **Sequence**, **Parallel** y **Graph**. Las decisiones
son funciones Python. Tools implementan operaciones; Skills las agrupan;
Environment mantiene episodios y memoria; Eval comprueba el resultado.
`run()` es el recorrido habitual. `compile()` prepara una declaración para
reutilizarla cuando hace falta.

Empieza en [tutorials](tutorials/README.md), elige una tarea en
[examples](examples/README.md) o abre [Studio](examples/agentic_systems_studio/README.md).
Los [seis flujos](examples/grammar_tour/README.md) muestran la gramática completa
de Agent y System con entrada, proceso y salida.

El [notebook de toda la API](examples/api_walkthrough/01_api_user_guide.ipynb)
reúne el recorrido y la aplicación de pedidos. El [inventario de notebooks](docs/NOTEBOOK_INVENTORY_213.md)
distingue material vigente, referencias compartidas e historia.

La revisión **2.1.3** está en este repositorio y no se ha publicado en esta tarea.
Instala el wheel local proporcionado; [instalación](INSTALL.md) explica la
preparación inicial y los SDK opcionales. No hay aliases ni compatibilidad con
los constructores anteriores.

Para elegir un proveedor o framework, consulta [integraciones](docs/API_213.md#runtime-y-framework).
Hay pruebas actuales con Python, Ollama, Bedrock API key y OpenAI API key.
[La validación final](revisions/2.1.3/closeout-evidence/REPORT.md) especifica modelos,
casos, artefacto, consumo y límites. IAM y GPU siguen requiriendo su entorno.

[Guía de API](docs/API_213.md) · [Referencia completa](docs/API_213_SURFACE.md) ·
[Criterios de experiencia](docs/USER_EXPERIENCE_213.md) · [Validadores](docs/VALIDATION_213.md)
