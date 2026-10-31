# Lineage y Memory entre agentes y ejecuciones

API local: **2.1.4.dev7**. [Código completo y explícito](example.py).

Input → Agent `fees` calcula comisión → Agent `reviewer` aplica la política → Output.
Ambos se coordinan con un Graph dentro de System. Cada Agent también tiene su Graph.
Todos los pasos son Python determinista; no hay inferencia.

`Context.data` aporta moneda, comisión y límite; `Context.sources` identifica la política.
El segundo agente recibe la observación del primero en `Context.lineage`.
`Memory(capacity=2)` se adjunta al System; después del primer run conserva un episodio.
Durante el segundo run ambos agentes reciben ese episodio en `Context.episodes`.
El linaje actual y el histórico se mantienen separados.

| Run | Agent | Context.lineage | Context.episodes |
|---|---|---|---|
| 1 · amount=5000 | fees | vacío | vacío |
| 1 · amount=5000 | reviewer | fees → fee=50 | vacío |
| 2 · amount=12000 | fees | vacío | ejecución 1 y su linaje compacto |
| 2 · amount=12000 | reviewer | fees → fee=120 | ejecución 1 y su linaje compacto |

El estado público solo contiene `amount`, `fee` y `decision`. Las capturas de Context
se registran en una lista de observación independiente; nunca se devuelven al Graph.
El estado interno utiliza referencias acotadas para enlazar evidencia.
La decisión usa la política y el pago actual: recordar una ejecución no modifica
automáticamente las reglas ni convierte un antecedente en verdad.

Con el SDK local dev7 y sus dependencias instaladas:

```console
python examples/lineage_memory/example.py
```

Desde este checkout, el runner añade bloqueo offline y verifica el wheel instalado:

```console
.venv/Scripts/python.exe revisions/2.1.4/grammar-dev7/lineage-memory/run_validation.py
```

Validación: dos ejecuciones correctas, cuatro capturas, dos episodios, cero inferencia
y cero intentos externos. `compile()` no ejecutó Tools ni escribió Memory.

- [Informe ejecutado: Context exactos y human_results](../../revisions/2.1.4/grammar-dev7/lineage-memory/REPORT.md)
- [Evidencia serializada y RunResults](../../revisions/2.1.4/grammar-dev7/lineage-memory/evidence.json)

Memory es local al proceso, sin persistencia ni búsqueda semántica. La validación
corresponde a este ejemplo y este wheel, no a nuevos bytes ni a proveedores externos.
