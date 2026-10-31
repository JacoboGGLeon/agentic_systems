> **Histórico: no es la guía de la API 2.1.4.dev3.** Conserva propuestas/resultados de su versión original. Para implementar, usa [la API vigente](API_214.md).

# Criterios de la API y del material de aprendizaje

El recorrido habitual es **importar → construir → run → resultado**. Agent y
System conservan los mismos flujos y el mismo contrato de ejecución. `compile`
es preparación opcional; no es un paso obligatorio ni otro constructor.

| Referencia | Patrón observado | Aplicación en esta librería |
|---|---|---|
| [pandas](https://pandas.pydata.org/docs/user_guide/10min.html) | Presenta objetos y operaciones mediante resultados pequeños | El primer ejemplo calcula y muestra `result.data`; el inventario completo queda como referencia |
| [scikit-learn](https://scikit-learn.org/stable/getting_started.html) | Un pipeline conserva la interfaz de sus componentes | Agent y System usan `run` tanto solos como compuestos |
| [PyTorch](https://docs.pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html) | Separa definición del modelo y ejecución | Declarar el flujo no ejecuta Tools ni modelos; compilar tampoco infiere |
| [NumPy](https://numpy.org/doc/stable/user/quickstart.html) | Introduce operaciones y salidas antes de opciones especializadas | Las primeras lecciones usan datos pequeños y expectativas visibles |
| [Polars](https://docs.pola.rs/user-guide/getting-started/) | Compone operaciones manteniendo su significado | Sequence, Parallel y Graph conservan el significado de cada paso |

Estas referencias orientan la experiencia; no implican copiar sus verbos.
Los verbos se eligen por su significado en esta API: `run` ejecuta una unidad
y devuelve `RunResult`; `compile` permite prepararla antes de ejecutar.

Las opciones se presentan cuando resuelven una necesidad. Tools y Skills
aparecen al reutilizar capacidades; Environment al procesar episodios; Eval al
comprobar resultados. Proveedores, SDKs nativos, async, límites y serving son
capítulos posteriores. Las firmas completas permanecen accesibles en la
[referencia](API_213_SURFACE.md).

Cada example tiene una entrada pequeña, el proceso y una salida verificable.
El código de validación, las rutas del repositorio y las banderas de campañas
viven en validadores, fuera de la entrada de aprendizaje. La configuración
externa tiene un propósito explícito y no aparece como un requisito para el
primer ejemplo.

Los estados describen qué ocurrió: ejecución offline, ejecución live,
configuración preparada o entorno pendiente. Los experimentos anteriores se
conservan como evidencia histórica junto a su adaptación actual. Los fixtures
de jueces y lenguaje creativo se identifican como tales.
