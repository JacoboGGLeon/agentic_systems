# Sistema financiero y harness compilado

Simulador de tesorería con la API local 2.1.4.dev7 build 03. No realiza
transferencias ni operaciones bancarias. Las cantidades son centavos MXN;
la política es ficticia y está declarada en Context.

[example.py](example.py) muestra las declaraciones de Tools, Skills, dos
Agents, Context, Memory, System, su compile, Environment y Eval. Solo importa
Pydantic y agentic_systems. No importa builders de otros ejemplos.

[progressive.py](progressive.py) construye otra variante por etapas: runtime
con controles de scheduler, tres Agents de actor con native/OpenAI Agents/
Strands, un Agent compuesto con grafo, inyección Runtime.context, System y
Limits raíz. Todos los actores usan Python, sin modelos reales.
[Su evidencia separada](../../../revisions/2.1.4/contracts-dev5/progressive-financial/summary.json)
explica el conteo exacto de ocho activaciones y el corte con siete.

El runtime es python-runtime y el actor usa native por defecto. Los dos
grafos son StateGraph originales de LangGraph. financial_harness es el nombre
local del ejecutable devuelto por financial_system.compile(); no existe un
constructor Harness nuevo.

## Input → proceso → output

Saldo inicial 100000 centavos, reserva 30000, revisión por encima de 30000.

| Registro | Importe | Proceso | Decisión | Saldo después |
| --- | ---: | --- | --- | ---: |
| P-001 | 12000 | Analista de disponibilidad → agente de política | approved | 88000 |
| P-002 | 40000 | Disponibilidad suficiente → supera umbral de aprobación | review | 88000 |
| P-003 | 90000 | Disponibilidad insuficiente → rama reject | rejected | 88000 |

Environment inyecta el saldo al observar cada registro y actualiza su estado
solo con el saldo resultante. review y rejected son resultados de negocio
válidos: el RunResult puede ser ok=True en ambos casos.

Memory retiene episodios de ejecución y linaje; no es el saldo contable.
Context aporta la política y sus fuentes. El estado del Environment lleva el
saldo. Las herramientas pueden consultar context.episodes como observaciones
previas; su contenido no cambia las reglas de autorización.

## Ejecución

Con el wheel local build 03 y sus dependencias instalado:

```bash
python examples/applications/financial_harness/example.py
```

run ejecuta una operación individual, un episodio de tres registros y una
Eval que vuelve a ejecutar ese episodio. Los componentes están declarados
explícitamente a nivel de módulo. La demostración registra siete ejecuciones
del System, con IDs distintos. No transfiere ni duplica pagos reales.

[Evidencia offline](../../../revisions/2.1.4/contracts-dev5/financial-harness/summary.json)
vinculada al wheel. No se atribuye aceptación online ni validación con otros
frameworks a esta ejecución Python/native. Los dos imports son suficientes
para declarar el ejemplo; la captura de evidencia usa biblioteca estándar en
un verificador separado.
