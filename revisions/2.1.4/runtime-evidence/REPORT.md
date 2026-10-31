# Runtimes reales · Qwen y OpenAI · 2.1.4.dev2

Wheel instalado sin modo editable: `3e618a64e013967cf654ca87b8283ca3c81ceef7b918805218e238196f638b56`. Sin publicación. La aceptación offline anterior se conserva intacta; este reporte añade evidencia live del mismo wheel.

Caso: interpretar una reclamación parcial, normalizar, calcular con Python, aplicar política en ramas, decidir, pausar y reanudar. Esperado: pedido R-17, falta una unidad de dos, reembolso 120 MXN. Eval determinista del resultado capturado, invariantes y linaje.

Los actores son native, openai-agents y strands; la orquestación es exclusivamente LangGraph. No se certifican aquí handoff, MCP/A2A, Studio ni todas las operaciones de cada SDK.

| Runtime / modelo | native | openai-agents | strands |
| --- | --- | --- | --- |
| Python | PASS | PASS | PASS |
| OpenAI gpt-4.1-mini | PASS | PASS | PASS |
| Bedrock Qwen3-32B | PASS | FAIL: JSON en Markdown | FAIL: JSON en Markdown |
| Ollama GPU Qwen3-4B Instruct 2507 Q4_K_M | PASS | PASS | PASS |
| Ollama Cloud, API key | Pendiente: catálogo sin Qwen | Pendiente | Pendiente |
| vLLM GPU, Qwen3-0.6B propuesto | Pendiente: sin servidor/WSL | Pendiente | Pendiente |

**12 celdas ejecutadas: 10 PASS y 2 FAIL; 6 celdas de rutas no disponibles. No está certificada toda la matriz.**

## Modelos curados y GPU

- Bedrock: `qwen.qwen3-32b-v1:0`, región us-east-2. API key/bearer, sin sustitución de modelo.
- Ollama local: `qwen3:4b-instruct-2507-q4_K_M`, tag del catálogo oficial; digest completo en preflight.json y cada inventario GPU.
- Cada una de las tres llamadas Ollama verificó `size_vram > 0` para ese modelo. Es asignación GPU acreditada, no un porcentaje de utilización medido por token.
- RTX 3070 Laptop GPU, 8192 MiB. API key cloud configurada; GET de catálogo sin Qwen. No se intentó generación cloud ni se usó Gemma.
- vLLM no respondió. No se instaló WSL ni se descargaron pesos; receta futura en ../../../docs/VLLM_GPU_214.md.

## Los dos fallos

Qwen devolvió los campos y cantidades esperados dentro de un único bloque Markdown. El texto completo no es JSON; el contrato rechazó la salida. El cuerpo del bloque sí pasa JSON Schema offline. Es una incompatibilidad de salida estructurada entre respuesta y adaptación, no un error de la aritmética Python. Los intentos siguen FAIL.

La corrección candidata sería normalización única y estricta de un solo bloque JSON, o structured output cuando el proveedor lo soporte, seguida siempre del mismo esquema. No se modificó el wheel ni se flexibilizó la aceptación para ocultar el fallo. Una corrección requerirá otro artefacto y validación correspondiente.

## Presupuesto y alcance

- Autorizado acumulado: USD 1 y 20 solicitudes.
- Anteriores dev1: 8 solicitudes, USD 0.031772 reservados; no certifican dev2.
- Esta campaña dev2: 9 solicitudes (3 OpenAI, 3 Bedrock, 3 Ollama); incluye los dos fallos.
- Acumulado: 17/20; reserva conservadora USD 0.085441.
- Restante: 3 solicitudes y USD 0.914559 de reserva.
- La reserva no es una factura: usa estimación conservadora por bytes/tokens y margen; no se reembolsan fallos. GPU local cuesta cero USD de API y cuenta solicitudes.
- Cero llamadas durante reanudación en las nueve celdas que llegaron a pausa. Evaluación posterior de capturas sin inferencia. Trabajadores terminados antes del cierre.

## Evidencia

- matrix.json: todas las celdas, RunResults y vistas de linaje humano/agente.
- Carpetas UTC: plan congelado antes de cada ejecución, resultados y contador persistente.
- output-analysis.json: reproducción offline del problema de Markdown, con el texto original.
- preflight.json: modelos, digest, GPU y disponibilidad de endpoints; sin credenciales.
- minimal-api-results.json y minimal-api-notebook.json: ejemplo integrado y notebook en kernel nuevo, guard offline, cero conexiones de aplicación.
- api-surface.json y ../../../docs/API_214_SURFACE.md: firmas reales de la API del wheel.
