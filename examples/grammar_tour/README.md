# Seis flujos con una gramática · 2.1.4

La composición y las aserciones están visibles en [el código](example.py).
Lee las declaraciones de Tools, Agents y Graph antes de ejecutar el ejemplo.

[example.py](example.py) declara seis grafos toolkit.Graph explícitos: Agent y
System, cada uno en secuencia, paralelo y con decisiones. LangGraph es el único
orquestador. Con value=3, los outputs son 8, 10 y 8 para ambos propietarios.
Con value=-3, la decisión conserva -2. Las aserciones verifican ambas ramas.

Tools calculan, Skill agrupa capacidades y System coordina Agents.
Environment recorre records con estado propio y Eval contrasta sus resultados.
run(input) y compile().run(input) tienen el mismo contrato RunResult.
No se ejecuta inferencia.

[Notebook integrado](../common_graph/01_common_graph.ipynb) ·
[Validación histórica dev5](../../docs/LEARNING_VALIDATION_214.md).

[Validación histórica dev5 de Pydantic y human_results](../../revisions/2.1.4/contracts-dev5/REPORT.md). Las revisiones previas se conservan como evidencia histórica.
