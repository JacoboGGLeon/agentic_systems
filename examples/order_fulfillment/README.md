# Pedidos — API única 2.1.3

Ejemplo canónico que importa solamente `agentic_systems`. Requiere el wheel
local 2.1.3; no funciona mediante aliases de 2.1.2 ni importa `unified_grammar`.

Input → Intake valida → Pricing e Inventory en paralelo → Policy decide →
Approve, Review o Reject devuelve una instrucción. Environment entrega seis
pedidos de negocio; Eval compara sus resultados y detecta una diferencia
incorrecta de un centavo. El séptimo caso conserva la cotización cuando falla
inventario. No se modifican existencias ni se contactan servicios externos.

La única declaración es `system.py:build_system`. Los datos y expectativas
están en `fixtures/`; las operaciones en `tools.py` y sus Skills en `skills.py`.

```text
python examples/order_fulfillment/run.py
```

Usa un proceso dedicado: el comprobador instala un guard offline que permanece
activo hasta cerrar ese proceso. Las rutas de inferencia no se ejecutan.
