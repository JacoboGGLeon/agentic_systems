# Estado de Environment y Memory · 2.1.4.dev7

Input: importes 2, 3 y 100. observe combina el siguiente importe con el total
actual; el Graph suma; update conserva el total. stop termina al alcanzar 5,
antes de consumir 100. Outputs: total=2 y total=5. Repetir run reinicia el
estado del episodio y produce los mismos totales con otro execution_id.

El acumulador es estado del Environment. Memory conserva episodios observados;
no participa en esta suma y no debe presentarse como aprendizaje. Para ver cómo
sí modifica una decisión, y cómo Eval aísla sus escrituras, consulta
[el notebook de lineage y Memory](../lineage_memory/01_lineage_memory_decisions.ipynb).

La composición y las aserciones están visibles en [el código](example.py).
Lee las declaraciones de Tools, Agents y Graph antes de ejecutar el ejemplo.

El código expone observe, update, stop y Graph. El replay determinista no implica
persistencia ni reanudación después de reiniciar el proceso.

[Declaración](example.py) · [Evidencia](../../revisions/2.1.4/grammar-dev7/examples-review/03/examples/examples--episode_memory--example.py.json)

Perfil actual: **offline-passed**. El catálogo [de validación](../../docs/LEARNING_VALIDATION_214.md) separa configuración, Python, servicios locales y pruebas de modelos. La evidencia 2.1.3 conservada es histórica y no certifica estos bytes.

[Validación histórica dev5 de Pydantic y human_results](../../revisions/2.1.4/contracts-dev5/REPORT.md). Las revisiones previas se conservan como evidencia histórica.
