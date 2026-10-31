# Sistema financiero paso a paso · 2.1.4

**Repetición actual:** [notebook con Ollama local/native restaurado](03_financial_system_native_local.executed.ipynb),
ejecutado sobre el wheel corregido junto con OpenAI/native, Bedrock/Strands y
Ollama cloud/OpenAI Agents. [Informe y presupuesto](../../revisions/2.1.4/ollama-connection-fix/01/live/REPORT.md).
La conexión native está ahora validada con local/cloud también en sync/arun.
Los notebooks y la tabla de abajo conservan los perfiles históricos, incluidos
el workaround Strands/local y el intento fallido anterior.

[Python ejecutado](01_financial_system.ipynb) ·
[Mezcla ejecutada](02_financial_system_mixed.executed.ipynb) ·
[Informe y evidencia](../../revisions/2.1.4/financial-mixed/01/REPORT.md).

El notebook declara Pydantic, runtimes, Tools, Skills, Context, Memory, Agents,
Graph, System con decisión, Environment con recompensa y Eval aislada.
No importa un constructor de aplicación de otro example.

| Paso | Python | Mixed |
|---|---|---|
| Comisión | Python/native | OpenAI gpt-4.1-mini/native |
| Auditoría | Python/native | Bedrock Qwen3-32B/Strands |
| Verificación local | Python/native | Ollama local Qwen3 4B/Strands |
| Verificación final | Python/native | Ollama cloud Gemma4:31b/OpenAI Agents |

Todos los grafos son LangGraph. Importes en centavos MXN; no se transfieren
fondos. Los modelos llaman Tools; Python calcula y aplica las reglas.
Input → validar → comisión → auditar linaje/Memory → verificar local/cloud
→ decisión → output. Un pago de 5000 se aprueba una vez y se revisa al repetirse.

La primera mezcla con Ollama local/native falló: ese actor toma el endpoint
global de Ollama en vez del declarado. El intento se conserva y no se cuenta
como PASS. La configuración final usa Strands/local con conexión explícita.
No se modifica el SDK ni se sustituyen modelos para declararlo resuelto.

El perfil por defecto al ejecutar las celdas es Python. Mixed requiere claves
en el entorno y un contador autorizado activo; no basta con cambiar el perfil.
Leer las salidas guardadas no consume inferencia. Las capturas completas de
RunResult, Context, Memory y linaje están en la evidencia del informe.

No valida amount:null de Bedrock, IAM/ADA, vLLM GPU, handoffs, MCP/A2A ni UI de Studio.
