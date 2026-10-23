# Agentic Systems 2.1.3 — candidata de revisión de API

Proyecto independiente generado para el challenge offline de pedidos. Esta
candidata usa el wheel publicado **agentic-systems 2.1.2** y una fachada
experimental vendorizada bajo `src/unified_grammar`. No es una publicación de
agentic-systems 2.1.3 ni cambia los exports o contratos heredados de 2.1.2.

## Ejecutar

En un entorno Python con las dependencias de `pyproject.toml` instaladas:

```text
python app.py --both
python test_offline.py
```

Abre `notebooks/01_order_challenge.ipynb` y ejecuta las celdas en orden en un
kernel dedicado. Los actores son operadores deterministas, no razonadores
simulados. El guard bloquea conexiones de aplicación y subprocesos hasta cerrar
el proceso/kernel. Jupyter y asyncio requieren su transporte local interno.

`.env.example` documenta el contrato; `.env` es opcional y no contiene claves.
AGENTIC_LIVE distinto de 0 y proveedores distintos de python-runtime se rechazan.

## Input → proceso → output

Pedido con identificador, país, moneda, presupuesto en centavos y líneas SKU.
Intake normaliza y valida. Pricing e Inventory trabajan en paralelo sobre copias
independientes. Policy decide aprobación, revisión humana o rechazo; el agente
terminal devuelve una instrucción, sin enviar mensajes ni modificar inventario.

Los siete casos cubren aprobación, presupuesto insuficiente, falta de stock,
revisión por importe, cantidad inválida, líneas SKU duplicadas y un fallo técnico
controlado de inventario. Rechazar un pedido es una ejecución correcta; el fallo
técnico devuelve RunResult.ok=false y conserva la cotización ya completada.

Environment procesa seis pedidos de negocio como episodios de un paso por
registro, con inventario fijo independiente. No simula reservas persistentes.
Eval compara los seis resultados exactos y un control negativo debe detectar
una diferencia de un centavo. No se usa juez LLM ni inferencia.

## Dónde modificar

- `src/order_challenge/system.py`: única declaración de Agents, System y flujos.
- `tools.py` y `skills.py`: operaciones y capacidades reales de 2.1.2.
- `fixtures/`: catálogo local y contratos esperados, versionados en JSON.
- `verification.py`: aceptación, historia, eventos, linaje y serialización.
- `manifest.json`: versión objetivo, baseline y estado real de validación.
- `evidence/`: resultados obtenidos; no confundir la plantilla con evidencia.

Los límites del runtime son cooperativos; no cancelan callbacks bloqueados.
No se valida aquí inferencia, IAM, ADA ni una entrega empresarial.
