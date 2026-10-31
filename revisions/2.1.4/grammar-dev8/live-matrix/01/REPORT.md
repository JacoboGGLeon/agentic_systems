# Matriz online · Agentic Systems 2.1.4.dev8

Resultado: **11/12 combinaciones funcionales en las configuraciones documentadas; aceptación completa bloqueada**.

No se cambió el SDK ni se publicó. Se usó el wheel instalado fuera del checkout: 14148af530c14660b888479f6a2eabb4ef1bf74637b7cc3244422f447b547e23.

## Matriz de configuración validada

| Runtime / modelo | native | openai-agents | strands |
|---|---|---|---|
| openai-runtime / gpt-4.1-mini | PASS · auto | PASS · auto | PASS · auto |
| bedrock-runtime / qwen.qwen3-32b-v1:0 | PASS · required | PASS · required | FAIL · auto y required |
| ollama-local / qwen3:4b-instruct-2507-q4_K_M | PASS · auto | PASS · auto | PASS · auto |
| ollama-cloud / gemma4:31b | PASS · auto | PASS · auto | PASS · auto |

**El perfil original auto pasó 9/12.** Bedrock falló en los tres frameworks por omitir audit_payment. El seguimiento cambió exclusivamente policy.tool_choice a required en los dos actores con Tools: pasaron native y OpenAI Agents; Strands siguió fallando. No se atribuye ese seguimiento al perfil auto ni se borran sus fallos.

Los 12 pilotos de generación JSON y los 12 perfiles negativos pasaron. Cada perfil negativo verifica entrada inválida y fallo de Tool antes del actor; consumió cero inferencia. La identidad del framework aparece en framework_adapter dentro de los RunResults guardados.

## Input → proceso → output

- System: SINGLE, amount=15000 → fee=150 → decision=review, status=pending_review.
- Environment: PAY-001, amount=5000, dos episodios → fee=50; primero approve, después review_duplicate por Memory. Estado final: processed=2, approved=1, reward=1. Reward es un agregado del ejemplo, no una API RL pública.
- Eval: EVAL-001, amount=5000, dos casos → approve en ambos, cada uno con una copia de la misma Memory previa; la Memory externa permanece idéntica. Aislar no equivale a vaciar Memory.
- Agent con Graph: validación determinista → actor de comisiones. Otro Agent con Graph ejecuta el actor auditor. El System coordina ambos y enruta la decisión; el Environment tiene su propio Graph.
- Tools Pydantic y Skills, Context con fuentes, linaje previo obligatorio, Memory, decisiones, serialización e invariantes. El estado conserva solo campos de negocio. Eval usa oráculos deterministas; no un juez LM.

Cada combinación completa comprueba una ejecución de System, dos episodios y dos casos de Eval. Los actores usan modelos reales para invocar Tools y producir JSON; las operaciones y reglas financieras siguen en las Tools deterministas. No se prueba razonamiento abierto o toda la superficie de los SDK.

## Defecto confirmado

[La captura offline](strands-policy-offline-proof.json) reproduce en el SDK instalado que policy.tool_choice=required llega a Bedrock como toolChoice.auto. Al proporcionar any directamente al stream del SDK, el request conserva any. No hubo red ni credenciales reales en esa prueba.
El hueco está entre _configure_model y ContractAwareBedrockModel.stream del adaptador Strands: la configuración plana de Bedrock solo recibe parámetros de generación; el selector requerido no se traslada. El servicio devolvió HTTP 200/end_turn y una decisión plausible sin invocar audit_payment; el contrato rechazó esa salida correctamente.
Corrección pendiente: trasladar la política al selector por turno, liberar la obligación después de satisfacer el contrato y conservar max_tool_calls y la continuación. Añadir regresiones para required/auto/none y generar otro wheel; después repetir la aceptación correspondiente. No se aplicó un bypass al wheel probado.

## Consumo y evidencia

294/300 solicitudes totales: 288 de inferencia y 6 de metadatos. Reserva conservadora USD 2.837193/10; quedan 6 solicitudes y USD 7.162807. No es una factura ni se devolvieron reservas por fallos. El contador anterior permanece intacto.
Despachos observados después del snapshot del trabajador: 0. El padre leyó el contador tras la salida de cada proceso; los hooks siguieron instalados mientras terminaban los trabajadores. No se promete preempción de una llamada remota.
La reserva de OpenAI usa las [tarifas oficiales del modelo](https://developers.openai.com/api/docs/models/gpt-4.1-mini). Para Bedrock y Ollama cloud se reservaron USD1/4 por millón de tokens de entrada/salida como techo de seguridad, contrastado con [AWS](https://aws.amazon.com/bedrock/pricing/) y [Ollama](https://ollama.com/pricing). Cada byte UTF-8 más framing se reserva como token de entrada, con salida máxima y margen del 25%; no se descuentan cachés.
Ollama local registró el Qwen con 3180247121 bytes de VRAM en [api/ps](gpu-observation.json). Ollama cloud resolvió gemma4:31b-cloud al slug gemma4:31b del mismo modelo, antes de congelar casos; no se sustituyó por otro modelo.

[Perfil y casos congelados](plan.json) · [Challenge visible](challenge.py) · [Seguimiento required](required-policy-plan.json) · [Contador](campaign-budget.json) · [Resumen](summary.json).

Cada JSON de trabajador conserva RunResults, Context recibidos, Memory antes/después de Eval, human_results y linaje. Los resultados originales están en runs/20261030T043436; el seguimiento separado está en required-policy-runs/20261030T044910.

## Pendientes

Strands + Bedrock sigue bloqueado. El caso antiguo amount:null no se repitió aquí, ni el System mixto de tres frameworks: supplement.py quedó preparado, sin ejecutarse. Tampoco se validan handoffs, MCP/A2A, toda la UI Studio, AWS/ADA IAM ni vLLM/GPU con esta campaña. No se amplía su aceptación por inferencia.
Con seis solicitudes no alcanza para repetir la matriz completa contra otro wheel. Se conserva el saldo y no se publica ni se declara certificación completa.
