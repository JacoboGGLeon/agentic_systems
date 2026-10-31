# Auditoría y validación · 2.1.4.dev3

La documentación y las implementaciones didácticas se migraron a una sola gramática. Se restauró el logo original y se actualizó la skill mantenida. **No se publicó. La aceptación online no está completa.**

[Informe de validación](../../../docs/LEARNING_VALIDATION_214.md) · [Inventario exhaustivo de notebooks](../../../docs/NOTEBOOK_INVENTORY_214.md) · [RunResults y linaje por archivo](../../../docs/RUNRESULTS_LINEAGE_214.md).

| Runtime / destino | native | OpenAI Agents | AWS Strands |
|---|---|---|---|
| Python | Offline aprobado | Offline aprobado | Offline aprobado |
| OpenAI API key · gpt-4.1-mini | Live aprobado | Live + handoff | Live + MCP/A2A |
| Bedrock API key · Qwen3-32B | Live básico aprobado; 1 caso negocio falló | Live + handoff | Live + MCP/A2A |
| Ollama GPU · Qwen3 4B | Live aprobado | Live + handoff | Live + MCP/A2A |
| Ollama cloud/API key · Qwen | Pendiente | Pendiente | Pendiente |
| vLLM GPU · Qwen | Pendiente | Pendiente | Pendiente |

Consumo: 282 solicitudes; USD 1.434815 reservados. Restan 18 solicitudes / USD 8.565185.

Conservación: before-learning.zip y audit-before.json documentan el punto inicial; todos los intentos live originales se mantienen. pre-format-sources.zip y format-provenance.json separan cambios de formato de correcciones semánticas; estas últimas tienen regresiones. Los cambios didácticos no modificaron el wheel del SDK.

Se pueden construir referencias robustas para tareas acotadas, con contratos, límites, decisiones, controles negativos y evidencia. La documentación actual permite reproducirlas. Las limitaciones de persistencia, servicios no disponibles y aceptación semántica incompleta impiden afirmar cobertura universal o preparación de producción.

Entrega local adicional: [Studio wheel](candidate/agentic_systems_studio-2.1.4.dev3-py3-none-any.whl)
y [skill portable](candidate/agentic-systems-skill-2.1.4.dev3.zip).
[Verificación de Studio instalado](studio-wheel-validation.json): 22 fuentes
idénticas, tres perfiles Python aprobados, cero inferencia.
[Verificación de la skill](skill-validation.json): esquema válido, proyecto
generado con test aprobado, manifiesto de hashes correcto e instalación personal
de Codex sincronizada. El ZIP para ChatGPT no implica instalación en la cuenta.

[Revisión de secretos](secret-scan.json): 903 archivos, cero coincidencias de
las tres claves configuradas. [Enlaces de documentación](documentation-links.json):
sin destinos locales rotos en las guías comprobadas.

[Plan congelado](live-plan.json) · [Ajuste balanceado](plan-amendments.json) · [Ajuste de contratos tipados](typed-example-amendment.json) · [Matriz reconciliada](matrix.json).
