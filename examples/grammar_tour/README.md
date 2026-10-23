# Gramática única, de Tool a Eval

[example.py](example.py) contiene las seis declaraciones explícitas. No hace
inferencia. Se ejecuta con el SDK 2.1.3 instalado y el extra LangGraph.

| Propietario | Flujo | Input | Proceso | Output |
|---|---|---|---|---|
| Agent | Sequence | value=3 | incrementar, después duplicar | value=8 |
| Agent | Parallel | value=3 | incrementar y duplicar el mismo input; sumar | value=10 |
| Agent | Graph | value=3 | incrementar; duplicar si es no negativo | value=8 |
| System | Sequence | value=3 | Agent incrementador, después Agent duplicador | value=8 |
| System | Parallel | value=3 | dos Agents sobre el mismo input; sumar | value=10 |
| System | Graph | value=3 | Agent incrementador; decidir si llamar al duplicador | value=8 |

Con value=-3, la decisión termina después de incrementar: output value=-2.
Cada declaración se ejecuta directamente y compilada en native y LangGraph.

Las Tools implementan operaciones; Skill las agrupa y aporta instrucciones;
Agent ejecuta su propio flujo; System coordina Agents. Environment repite el
mismo System sobre records y mantiene memoria. Eval contrasta resultados exactos
y checks. Eval puede observar tanto una unidad como un Environment completo.

`run` ejecuta. `compile` prepara la misma declaración para reutilizarla:
`unit.run(input)` y `unit.compile().run(input)` conservan el contrato RunResult.
No hay que compilar antes de llamar run.

```python
from examples.grammar_tour.example import run

report = run()
report["rows"]
```

Las opciones de proveedor/framework se declaran en un Agent de runtime. Eso
cambia quién ejecuta el actor; el System y sus flujos conservan esta gramática.
