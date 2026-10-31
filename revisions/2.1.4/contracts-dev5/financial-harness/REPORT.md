# Ejemplo financiero · Python/native · build 03

Ejecutado contra el wheel local 2.1.4.dev5 build 03, instalado fuera del
repositorio. SHA-256:
df328e52d7a2660d7b29ce45a40c689766ce99196c02d5672930dd5663bbde34.

[Fuente completa](../../../../../examples/applications/financial_harness/example.py) ·
[Gramática completa](../../../../../docs/GRAMMAR_214.md) ·
[Resumen verificable](summary.json) · [RunResults, Memory y linaje](runresults.json) ·
[Controles de frontera y contratos](controls.json).

| Input | Proceso real | Output observado |
| --- | --- | --- |
| Saldo 100000, importe 12000 | Analista de disponibilidad → agente de política | approved, saldo 88000 |
| Saldo 88000, importe 40000 | Disponibilidad 58000 → umbral 30000 | review, saldo 88000 |
| Saldo 88000, importe 90000 | Importe superior a disponibilidad → rama reject | rejected, saldo 88000 |
| Tres registros y saldo inicial | Environment observa, llama al harness compilado y actualiza | Tres procesados, saldo final 88000, records_exhausted |
| Mismo episodio y expectativas congeladas | Eval vuelve a ejecutar los registros y comprueba decisiones, saldos e invariantes | 1 caso aprobado, 0 fallidos |

Moneda MXN, cantidades expresadas en centavos. Política ficticia; no hay
transferencias bancarias. approved/review/rejected son decisiones de negocio,
no valores del campo ok de ejecución. review no pausa el programa ni simula
la aprobación de una persona.

La demostración produjo siete entradas de Memory: una ejecución individual,
tres del Environment y tres de Eval. El saldo pertenece al estado episódico;
Memory conserva resultados/linaje y Context conserva política/fuentes.
Cinco controles de frontera pasaron. Otros cinco inputs inválidos
(cero, negativo, None, cadena y booleano) fueron rechazados antes de Tools.

Se contrastaron los 17 nombres core, seis reexportaciones LangGraph y
__version__ con __all__ del wheel. Este ejemplo referencia 12 nombres core y
tres de LangGraph, sin constructores nuevos. La composición está visible;
run solo reúne las ejecuciones y comprobaciones.

Cero solicitudes de inferencia y cero intentos de red bajo el bloqueo offline.
El ledger de campaña sigue en 148/150 y conserva su hash. No se certifican
otros frameworks o proveedores con esta ejecución, ni cambia la aceptación
global previa. Análisis estático del ejemplo y git diff --check aprobados.
