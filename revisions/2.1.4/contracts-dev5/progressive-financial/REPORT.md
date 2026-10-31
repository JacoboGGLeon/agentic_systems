# Construcción progresiva y alcance de Limits

Wheel local 2.1.4.dev5 build 03 instalado fuera del repositorio:
df328e52d7a2660d7b29ce45a40c689766ce99196c02d5672930dd5663bbde34.

[Fuente explícita](../../../../../examples/applications/financial_harness/progressive.py) ·
[Resumen](summary.json) · [RunResults y linaje](runresults.json).

Reglas de cotización ficticias, cantidades en centavos MXN:
10000 → añadir 500 con native → 10500 → descuento del 10% con OpenAI
Agents → 9450 → Strands compara con presupuesto 9000 → review.
Los tres SDKs utilizan python-runtime y sus adaptadores deterministas,
no modelos de lenguaje ni llamadas a servicios.

El Agent compuesto contiene nodos policy/fee/discount. El nodo policy recibe
el Runtime original de LangGraph, cuyo context contiene el Context declarado
en el System. Es distinto del objeto de configuración creado por runtime.

El resultado completo conserva amount_cents=9450, currency=MXN,
budget_cents=9000 y decision=review, con invariantes aprobados.
Se observaron tres Tool calls y ocho activaciones instrumentadas:
dos nodos del System, tres del Agent compuesto y tres nodos de actor.

| max_actions | Activaciones consumidas | Tools ejecutadas | Resultado |
| ---: | ---: | ---: | --- |
| 1 | 1 | 0 | failed |
| 6 | 6 | 2 | failed |
| 7 | 7 | 2 | failed |
| 8 | 8 | 3 | completed |
| 9 | 8 | 3 | completed |

Con cuota insuficiente el contador no excede el límite y la Tool assess no
se ejecuta. El fee_agent aislado consumió una activación y produjo 10500;
ese mismo actor, anidado, hereda el contador raíz. Cada actor conserva
max_tool_calls=1: el System ejecutó tres Tools en total, no una.
Todos los RunResults de éxito y fallo conservaron invariantes válidos.

Actor describe una responsabilidad de ejecución, no un constructor público.
Agent es la unidad pública y puede tener runtime o graph. El Agent compuesto
no tiene runtime propio; sus actores sí. Compartir el objeto de configuración
no convierte sus cuotas locales en un contador global compartido.

Cero intentos de red y cero inferencias bajo el bloqueo offline. El ledger
conserva 148/150 solicitudes y su hash anterior. La ejecución prueba los SDKs
con Python; no acredita semántica de modelos reales ni aceptación live.
