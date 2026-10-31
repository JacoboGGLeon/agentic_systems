# Graph, Tools Pydantic y resultados · 2.1.4.dev7

[Notebook explícito](01_checked_composition.ipynb) · [Programa](example.py).
El identificador de carpeta es histórico; la API actual no contiene check.

Input 5000 centavos → Agent con Graph calcula fee=50 y total=5050 → Agent
revisor aplica Context → System aprueba. Environment procesa también 12000 y
obtiene pending_review. Las Tools reciben/devuelven modelos Pydantic; sus
contratos rechazan ausencias, valores incorrectos y entradas adicionales.

compile prepara sin ejecutar negocio. Eval comprueba ambos casos con vistas
de Memory aisladas: el número de episodios de producción permanece en tres.
human_results muestra entradas, operaciones y decisiones sin repetir IDs de
wrappers. El detalle completo sigue en RunResult.to_dict/lineage.

La recompensa se calcula explícitamente en update y se conserva en state/history.
Coincidir con el oráculo del Environment suma uno; total_reward termina en dos.
El oráculo no se pasa al System. No hay reward= ni entrenamiento automático.

[API](../../docs/API_214.md) · [Informe](../../revisions/2.1.4/grammar-dev7/REPORT.md).
