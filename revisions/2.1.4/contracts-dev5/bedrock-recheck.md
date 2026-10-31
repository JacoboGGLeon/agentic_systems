# Bedrock: formato, piloto y repetición controlada

La clave actual es de corta duración. Se comprobó su estructura sin imprimir
credenciales y el piloto autenticado pasó. El validador anterior reconocía
solo claves largas ABSK: era incompleto. Ahora admite también el formato corto
bedrock-api-key-, con ocho regresiones offline. Ambos formatos están descritos
por [AWS](https://aws.amazon.com/blogs/security/securing-amazon-bedrock-api-keys-best-practices-for-implementation-and-management/).
La corrección afecta al harness de validación, no al SDK ni al wheel aprobado.

Se conservan Qwen qwen.qwen3-32b-v1:0, us-east-2, el mismo endpoint y el wheel
2.1.4.dev5. No se cambió a IAM ni se sustituyó el modelo.

| Prueba | native | OpenAI Agents | Strands |
| --- | --- | --- | --- |
| Notebook básico con Tool | PASS (piloto) | PASS | PASS |
| Reembolso con pausa/reanudación | PASS | PASS | PASS |
| Caso obligatorio amount:null | FAIL | FAIL | FAIL |
| Studio: historial y calculadora | Pendiente por saldo | Pendiente por saldo | Pendiente por saldo |
| MCP/A2A con servicio local y LM | No aplica a esta prueba | No aplica a esta prueba | PASS / PASS |

El caso obligatorio vuelve a fallar: en rows.1 la Tool recibe {"id":1}
cuando la entrada exige conservar {"id":1,"amount":null}. Pydantic rechaza el
campo ausente. No se añadió un valor por defecto ni se presentó ese fallo como
PASS. No se atribuye a un fallo de autenticación: el piloto, la matriz y las
otras aplicaciones sí autenticaron y ejecutaron correctamente.

Consumo de esta continuación: **19/21 solicitudes**. Acumulado: **148/150**,
**USD 0.875040/5 reservados**, no factura. Quedan dos solicitudes; Studio
ha necesitado tres por caso y no se inició. El control de presupuesto permaneció
activo hasta terminar los trabajadores. No se publicó.

La suite offline pasó **299 pruebas**. Se conservan los resultados previos de
27 notebooks, 54 entrypoints y el perfil local de protocolos sobre el mismo
wheel. La interoperabilidad Ollama cloud con salida final vacía sigue fallida;
no se repitió con el saldo reservado para Bedrock.

[JSON y enlaces a intentos](bedrock-recheck.json) · [Contador](campaign-budget.json) ·
[Informe completo](REPORT.md) · [Pendientes](../../../docs/OPEN_ISSUES_214.md).
