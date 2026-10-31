# Desarrollo acumulativo 2.1.4

Versión temporal: **2.1.4.dev0**. Sin publicación, tag de release ni inferencia.

- [Contratos](../../docs/CONTRACTS_214.md).
- [Gramática mínima](../../docs/GRAMMAR_214.md).
- [Ideas, decisiones y pendientes](../../docs/IDEAS_214.md).
- [Ejemplo ejecutable](../../examples/context_memory_lineage/README.md).
- `validation.json`: artefacto, hashes, pruebas y resultados offline medidos.
- `example-results.json`: RunResults, contexto para agentes y presentación humana.

La primera iteración conecta Context y memoria episódica, corrige el recorte de
linaje y la delegación con límites, introduce fuentes lazy y separa `state` de Memory.
Se conserva la evidencia de 2.1.3 en su revisión; no acredita automáticamente esta versión.

Pendientes: persistencia de memoria, IR común extensible, entorno interactivo
reset/step, delegación como capacidad, retirada del mini-DSL histórico de Python,
pseudocódigo, certificación live y migración/ejecución del catálogo completo de
tutorials y examples sobre 2.1.4. El notebook nuevo es la referencia de este prototipo.
