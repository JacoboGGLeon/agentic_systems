# Gramática 2.1.3

La revisión está implementada: Agent y System reciben Sequence, Parallel o
Graph; las decisiones son funciones directas. Ambos ejecutan con `run` y
permiten preparar con `compile`. Tools, Skills, Environment y Eval conservan
RunResult como resultado común.

Empieza por [tutorials](../tutorials/README.md) o [los seis flujos](../examples/grammar_tour/README.md).
La [referencia](API_213.md) y el [inventario](API_213_SURFACE.md) detallan contratos.
[Los criterios de experiencia](USER_EXPERIENCE_213.md) explican la enseñanza
progresiva, tomando como referencia bibliotecas conocidas.

Las propuestas de compatibilidad previas quedaron sustituidas por la decisión
de una sola API. Se conserva el [plan histórico](../revisions/2.1.3/grammar-plan-history.md).
[El informe actual](../revisions/2.1.3/framework-evidence/REPORT.md) separa
pruebas offline, live y entornos pendientes. La revisión permanece sin publicar.
