# Roadmap

**2.1.3 está publicada:** API única de Agent y System con Sequence, Parallel,
Graph, decisiones Python, run/arun y compile opcional. Tools, Skills,
Environment, Eval y RunResult forman el mismo contrato. La validación original
está en [el cierre del release](revisions/2.1.3/closeout-evidence/REPORT.md).

El trabajo actual mejora la experiencia de aprendizaje: tutorials por core,
providers, frameworks y API; examples ejecutables; Studio visible y fácil de
instalar; evidencia por fuente. Las mejoras de documentación no reemplazan los
bytes publicados. La [nueva validación](docs/LEARNING_VALIDATION_213.md) tiene
su propia autorización de USD 10 y 300 llamadas.

Las siguientes validaciones requieren sus entornos: vLLM/Colab GPU, AWS IAM y
ADA IAM. Pueden ampliar la evidencia del wheel publicado; una corrección de
software requeriría otra versión. No se presentará una configuración como una
prueba ejecutada en GPU o IAM.

La entrega empresarial, el extra `[ada]`, ADA Studio y su wallet son trabajo
posterior. La wallet requiere el diseño que aporte el usuario. No son
capacidades instaladas ni validadas en 2.1.3.

La evolución conserva una gramática por concepto, configuración explícita,
SDKs opcionales cargados cuando se necesitan y ejemplos que enseñan el código
que ejecutan. Los experimentos históricos conservan su procedencia; no crean
formas adicionales de construir agentes o sistemas.
