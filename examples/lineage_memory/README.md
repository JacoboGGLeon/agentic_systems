# Lineage y Memory entre agentes y ejecuciones

API local: **2.1.4**. [Notebook ejecutado, con composición visible](01_lineage_memory_decisions.ipynb) · [Código completo y explícito](example.py).

El notebook contiene los Context completos de las dos ejecuciones, Environment
y Eval, human_results y tres controles causales, con verificaciones de estado
y memoria. Validado offline en un kernel limpio: 18 celdas de código, ninguna omitida.
La evidencia y el primer intento corregido se conservan en
[notebook-validation](../../revisions/2.1.4/grammar-dev7/lineage-memory/notebook-validation/).

Input → Agent `fees` calcula comisión → Agent `reviewer` aplica la política → Output.
Ambos se coordinan con un Graph dentro de System. Cada Agent también tiene su Graph.
Todos los pasos son Python determinista; no hay inferencia.

`Context.data` aporta moneda, comisión y límite; `Context.sources` identifica la política.
El segundo agente exige una observación exitosa del primero en `Context.lineage`
y verifica que fee coincide con esa observación y con la política actual.
`Memory(capacity=2)` se adjunta al System; después del primer run conserva un episodio.
Durante el segundo run ambos agentes reciben ese episodio en `Context.episodes`.
El revisor consulta su linaje estructurado: si el mismo payment_id ya fue aprobado,
devuelve review_duplicate. Los dos runs tienen exactamente el mismo input.
El linaje actual y el histórico se mantienen separados.

Environment procesa PAY-002 dos veces: approve y review_duplicate. Su update
captura la Memory del System después de cada episodio; con capacidad dos cambian
los IDs retenidos, aunque la longitud se mantiene en dos. Cada decisión correcta
suma una recompensa explícita; total_reward=2.

Eval ejecuta dos casos del mismo Environment, cada uno con PAY-003 repetido.
Dentro del caso la memoria cambia y produce approve/review_duplicate. Ambos
casos empiezan con los mismos IDs de producción; las escrituras de un caso no
pasan al siguiente y Memory.read() antes/después de Eval es exactamente igual.
Los checks que leen Memory mediante un cierre ven también la vista aislada.
La auditoría en listas externas sigue acumulando observaciones: Eval no aísla
variables arbitrarias, clientes, archivos ni otros efectos externos.

| Run | Agent | Context.lineage | Context.episodes |
|---|---|---|---|
| 1 · PAY-001, amount=5000 | fees | vacío | vacío |
| 1 · PAY-001, amount=5000 | reviewer | fees → fee=50 | vacío → approve |
| 2 · PAY-001, amount=5000 | fees | vacío | ejecución 1 y su linaje compacto |
| 2 · PAY-001, amount=5000 | reviewer | fees → fee=50 | ejecución 1 → review_duplicate |

El estado público solo contiene `payment_id`, `amount`, `fee` y `decision`. Las capturas de Context
se registran en una lista de observación independiente; nunca se devuelven al Graph.
El estado interno utiliza referencias acotadas para enlazar evidencia.
La decisión usa evidencia actual y aprobaciones anteriores del mismo identificador.
La política es explícita; la memoria no aprende ni modifica reglas automáticamente.

Controles offline ejecutados:

- Mismo input, sin Memory: approve. Con el episodio anterior: review_duplicate.
- Sin linaje previo de fees: error; los campos de negocio por sí solos no autorizan.
- Fee=51 con linaje pero fuera de política: error; registrar algo no lo vuelve correcto.

Context también contiene política y fuentes externas. Se puede presentar solamente
su linaje, pero esa proyección no es el Context completo. El informe conserva ambos
conceptos separados y los cuatro snapshots exactos.

Con el SDK local dev7 y sus dependencias instaladas:

```console
python examples/lineage_memory/example.py
```

Desde este checkout, el runner añade bloqueo offline y verifica el wheel instalado:

```console
.venv/Scripts/python.exe revisions/2.1.4/grammar-dev7/lineage-memory/run_validation.py
```

Validación: dos ejecuciones correctas, cuatro capturas principales, tres controles,
dos episodios, cero inferencia
y cero intentos externos. `compile()` no ejecutó Tools ni escribió Memory.

- [Informe ejecutado: Context exactos y human_results](../../revisions/2.1.4/grammar-dev7/lineage-memory/REPORT.md)
- [Evidencia serializada y RunResults](../../revisions/2.1.4/grammar-dev7/lineage-memory/evidence.json)

Memory es local al proceso, sin persistencia ni búsqueda semántica. La detección
de duplicados solo alcanza los episodios retenidos y su resumen: no es un registro
persistente de idempotencia ni evita carreras concurrentes. La validación
corresponde a este ejemplo y este wheel, no a nuevos bytes ni a proveedores externos.
