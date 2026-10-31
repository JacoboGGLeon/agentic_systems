# Pendientes observados · 2.1.4.dev8

## Endpoint de Ollama native en un System heterogéneo

Actualización: [corrección y regresiones offline](../revisions/2.1.4/ollama-connection-fix/01/REPORT.md).
El nuevo wheel resuelve conexión por actor y cierra clientes propios sin mutar
variables globales. La [repetición online](../revisions/2.1.4/ollama-connection-fix/01/live/REPORT.md)
pasó pilotos, dos ejecuciones sync, dos arun y el notebook original con local/native.
La regresión específica queda validada para esos bytes; los resultados históricos
siguientes describen la implementación anterior.

El [notebook financiero mixto](../examples/financial_mixed/README.md) detectó que
el actor native de Ollama toma endpoint/clave de variables globales en vez de la
conexión explícita. Al mezclar local y cloud en el mismo proceso, el contador
rechazó la ruta incompatible antes de transporte. El intento falló y se conserva.
La configuración final del example usa Strands/local y OpenAI Agents/cloud y pasa;
eso no corregía ni certificaba el caso native original. Esto motivó propagar conexión
por actor y añadir regresiones de coexistencia sin mutaciones globales. Ese example
no modificó el SDK; el parche posterior y su repetición online ya cubren esa ruta.

La [revisión posterior de defectos](../revisions/2.1.4/problem-fixes/01/REPORT.md)
separa correcciones offline y repeticiones online de los intentos históricos
descritos debajo. Estos últimos se conservan y no certifican el wheel nuevo.

## Interoperabilidad con Ollama cloud

El caso `three-framework-interop` usa Gemma4:31b, runtime Ollama y tres actores
en el mismo System. Input value=42/trail=[]; cada Tool debe sumar uno y dejar
su identidad; output esperado value=45/trail=[native, openai-agents, strands].

El intento dev5 aprobado para OpenAI y Ollama GPU falló en cloud: el primer
actor native ejecutó mark_native correctamente y registró value=43, pero el
proveedor terminó con `Provider returned an empty model output`. El System
conservó el fallo. Debe investigarse la interacción entre respuesta final,
finalización del bucle y contrato de Tools; no se atribuye definitivamente a
modelo o adaptador sin ese análisis. No se convierte el evento exitoso en un
PASS de toda la ejecución.

Ese caso permanece fallido. Los PASS cloud del notebook básico, reembolso,
Studio o MCP/A2A no lo sustituyen. La evidencia está en el
[resumen de todos los intentos](../revisions/2.1.4/contracts-dev5/summary.json).

## Bedrock

Los primeros tres notebooks fallaron por token expirado. Tras la confirmación
de renovación, el servicio rechazó el formato de la credencial; esa repetición
registró 14 solicitudes fallidas. La comprobación local posterior era
incompleta: solo reconocía claves largas ABSK, no claves cortas
bedrock-api-key-. Se corrigió con ocho regresiones offline para ambos formatos.
El piloto con la clave corta actual pasó y recuperó la autenticación.
La clave nunca se imprime ni se persiste en evidencia.

La matriz básica, reembolso y MCP/A2A pasaron con Bedrock. El caso obligatorio
de negocio volvió a fallar en native, OpenAI Agents y Strands: la Tool recibió
una fila sin amount:null y Pydantic rechazó el campo ausente. No se declara
arreglado ni se sustituye el nulo por un valor calculado. No se cambió a IAM.

Studio/Bedrock queda pendiente en los tres actores por presupuesto. El cierre
registró 148/150 solicitudes; las dos restantes no alcanzan para un caso de
Studio, cuyo protocolo observado necesita tres. [Repetición y evidencia](../revisions/2.1.4/contracts-dev5/bedrock-recheck.md).

La investigación posterior confirmó que el prompt y el esquema contenían el
nulo, pero la respuesta del servicio ya omitía el campo antes de la validación.
Build 03 activa strict tool use para el Qwen configurado y esquemas compatibles,
sin modificar el contrato. Las regresiones offline cubren los tres SDKs y
siguen rechazando campos omitidos antes de efectos. Esto corrige una carencia
de la petición; no demuestra aún que Bedrock preserve el nulo en vivo. Los
fallos anteriores siguen abiertos hasta repetir el caso con el nuevo wheel.
[Corrección y presupuesto de cierre](../revisions/2.1.4/contracts-dev5/bedrock-null-fix/REPORT.md).

## Aceptación estable

Dev8 es local. Los workflows ya están preparados; faltan la CI remota
Python 3.10–3.14 y el cierre live de los fallos obligatorios. vLLM está aplazado por decisión del usuario;
AWS IAM/ADA IAM requieren sus entornos. Memory y continuaciones no ofrecen
recuperación durable. [Estado](STATUS_214.md) · [Release](RELEASE_214.md).
