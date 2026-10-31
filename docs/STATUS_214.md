# Estado de 2.1.4.dev8

Última corrección: [Ollama native por actor](../revisions/2.1.4/ollama-connection-fix/01/live/REPORT.md).
544 tests offline y la repetición online específica pasan sobre el nuevo wheel:
local/cloud native sync/arun y notebook financiero original. Campaña nueva:
58/70 solicitudes, USD 0.493025 reservados. No se publica ni se transfiere toda
la aceptación histórica. amount:null Bedrock/Qwen sigue siendo un bloqueo separado.

Revisión posterior: [correcciones y validación de proveedores](../revisions/2.1.4/problem-fixes/01/REPORT.md).
El wheel corregido es distinto del anterior: su aceptación se registra por hash,
sin transferir los PASS históricos. La suite instalada pasa 529 pruebas offline;
la nueva campaña autorizada tiene topes independientes de USD 10 y 350 solicitudes.
Consultar ese informe para resultados online y pendientes; no hay publicación.

Campaña histórica anterior a estas correcciones: [matriz y resultados](VALIDATION_MATRIX_214_DEV8.md).
Nueve combinaciones pasaron con auto y dos Bedrock adicionales con required.
En aquel wheel, Strands + Bedrock estaba bloqueado por la traducción de tool_choice.
El wheel corregido pasó ese challenge y Studio/Bedrock con los tres actores;
el System mixto pasó en las cuatro rutas. El caso exacto amount:null sigue fallido
y bloquea aceptación. Consultar el informe posterior para hashes y contadores.

Revisión local sin publicar, sin PR nuevo ni ejecución remota de CI. Se preservan
los artefactos dev7 y los intentos dev8. La versión pública estable sigue siendo
2.1.3 según la última comprobación; este árbol no la modifica.

Graph es el nombre único del builder original de LangGraph. compile prepara,
run/arun ejecutan y RunResult conserva evidencia. Native, OpenAI Agents y Strands
son actores. Pydantic gobierna datos y configuración; Context, Memory, Environment
y Eval conservan los contratos de dev7.

Dev8 añade session= al runtime Bedrock y un complemento ADA independiente de
solo diagnóstico. La sesión selecciona IAM, queda fuera de datos serializados y
no provoca cambios globales de IMDS. El acceso compartido dentro del toolkit se
serializa; no se promete seguridad para usos externos ni persistencia del recurso.
[Contrato AWS/ADA](ADA_214.md).

El compilador reconoce propietarios callable y métodos ligados: valida hijos y
rechaza ciclos. CLI documenta su alcance, no sobrescribe destinos existentes y
genera un proyecto con tests, un ejemplo explícito y un notebook completo.

La suite canónica está en testpaths y se comparte con el runner y CI. La matriz
preparada construye un solo wheel y lo usa en Python 3.10–3.14. La aceptación local
se ejecuta con Python 3.14.2; no se atribuye un PASS remoto a otras versiones.
[Informe y cifras verificadas](../revisions/2.1.4/grammar-dev8/REPORT.md).

Pendientes: aceptación live de estos bytes, CI remota, Bedrock/null y Studio con
modelos reales, rutas Ollama configuradas, vLLM GPU y AWS/ADA IAM reales. Los
paquetes de Studio y ADA tienen alcances de prueba distintos; una conversación
fixture no certifica todos los controles UI ni la autenticación empresarial.

No hay recuperación durable de Memory/continuaciones, rollback general, API RL
completa ni ADA Studio con wallet. Ninguna de esas capacidades se anuncia como
implementada. Cero inferencia en este cierre; la campaña dev5 se conserva.

[API](API_214.md) · [Firmas](API_214_SURFACE.md) · [Inventario](NOTEBOOK_INVENTORY_214.md)
