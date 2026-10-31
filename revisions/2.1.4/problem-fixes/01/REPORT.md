# Correcciones y validación — 2.1.4.dev8

Trabajo local autorizado, sin publicación. La aceptación del release sigue bloqueada por el caso exacto de nulabilidad Bedrock/Qwen.

## Resultado final

| Control | Resultado |
|---|---|
| Suite canónica instalada | 529 PASS, cero inferencia |
| Examples offline | 58 PASS; uno de protocolos con perfil separado |
| Notebooks offline | 30 PASS; 12 celdas live/local omitidas |
| Lint / tipado vigente / secretos | PASS; tipado 0 errores y 0 avisos |
| Pilotos online | 12/12 PASS |
| Controles negativos de la matriz | 12/12 PASS, cero inferencia |
| Composiciones online | 12/12 PASS: cuatro rutas × tres frameworks |
| System mixto de tres frameworks | 4/4 PASS |
| Studio controlador + Bedrock | 3/3 PASS |
| Entrada exacta con amount:null + Bedrock | FAIL en los tres frameworks; bloqueo conservado |

Contabilidad final: **300/350 solicitudes**, todas de inferencia; **USD 2.807655** reservados conservadoramente de USD 10, no factura. Quedan 50 solicitudes y USD 7.192345 de reserva. Los trabajadores terminaron; no se desactivaron los hooks antes de su salida. Los dos ledgers históricos no cambiaron. [Resumen estructurado](summary.json).

La matriz financiera es satisfactoria, pero no convierte los casos de nulabilidad fallidos en aceptación. `release_ready=false`; no se publica.

## Cambios

- Strands/Bedrock conserva `required` por invocación, lo convierte a `any` y libera la selección forzada al cumplir el contrato o agotar presupuesto.
- `none` no envía Tools en Bedrock; los tres adaptadores rechazan ToolUse inesperado antes de efectos.
- OpenAI Agents conserva el vacío y lo rechaza, distinguiéndolo de valores válidos como cero, falso y campos nulos.
- El bucle native OpenAI/Ollama distingue llamadas rechazadas de una respuesta verdaderamente vacía y conserva la lista de rechazos.
- Native Bedrock conserva el fallo de síntesis y el trabajo de Tools, cuenta el despacho fallido y no continúa con una petición implícita. El consumo de tokens de un intento sin respuesta queda desconocido, no se inventa.
- Studio comprueba números contra evidencia calculada y rechaza contradicciones u omisiones del resultado. Esto no es un verificador semántico universal de prosa. El calculador pide Tool obligatoria.
- Se reconstruye Studio, incluido su laboratorio actualizado sin `Limits` ni LangGraph como actor.

La gramática pública no cambia. No se relajan esquemas, añaden defaults ni sustituyen modelos para esconder fallos. El parche previo de esquemas estrictos/nulos se mantiene.

## Offline

529 pruebas de la suite canónica pasan sobre el SDK y Studio finales instalados fuera del checkout (`final-all-junit.xml`); cero inferencia y cero intentos de red de aplicación. Incluyen 60 nuevas ejecuciones de regresión y las 23 existentes de nulabilidad/esquemas Bedrock. Hay 14 avisos de dependencias/importación, sin fallo.

La primera prueba instalada tuvo un error de colección porque faltaba el paquete diagnóstico ADA; se instaló su wheel local existente y se repitió la suite completa. No se accedió a IAM/ADA. Los intentos y logs se preservan. La suite source anterior pasó 514 casos antes de añadir doce comprobaciones adicionales.

58 entrypoints de examples pasan offline; otro de protocolos Strands conserva su perfil local separado y no se cuenta como PASS. Los 30 notebooks pasan con 12 celdas live/local omitidas explícitamente. Las celdas live no se consideran ejecutadas por el perfil offline. En la primera pasada, `tutorials/core/01_tools_skills.ipynb` no arrancó su kernel en 60 segundos; se repitió sin cambios de celdas y pasó. Se conservan ambos intentos. Jupyter también emitió un aviso de cleanup atexit; no se ocultó ni se contó el timeout original como PASS.

El example de sesión AWS requirió dos repeticiones de infraestructura: instalar el diagnóstico ADA faltante y precargar `platform.platform()` antes del guard para evitar el subprocess de detección de Windows que usa Botocore en su user-agent. No se modifica el example ni se habilitan subprocesses de aplicación; la repetición final tiene cero intentos bloqueados. Los fallos previos se conservan en `examples-retry*`.

## Artefactos

SDK: `build02/dist/agentic_systems-2.1.4.dev8-py3-none-any.whl`, SHA-256 `3fe02c467f5dd71855dfbdce95029393b893c773211bf6307700cb9e243238dd`.

Studio final: `studio-build03/dist/agentic_systems_studio-2.1.4.dev8-py3-none-any.whl`, SHA-256 `c732d77a10c396fdaa0744f18b39d016a74ceefbb7f44775c3c10d5d1b7ca792`.

El build02 de Studio reutilizó `build/lib` obsoleto de setuptools; la comparación completa detectó la discrepancia antes de aceptar el laboratorio. Se preserva ese intento. El build03 usa staging limpio: sus 22 archivos de payload coinciden con source e instalación. Los 117 del SDK también coinciden. `scripts/build_studio_candidate.py` deja este procedimiento reproducible y tres regresiones ejecutan el laboratorio Python instalado. El controlador de conversación y el contador no cambiaron entre ambos builds; las pruebas online de Studio usan el final.

Son builds privados separados de los anteriores, no reemplazos de publicaciones. `installation.json` registra su instalación no editable fuera del checkout. El commit base no representa por sí solo todos los cambios: el manifiesto liga bytes de source y paquetes.

## Campaña online

Autorización nueva: máximo USD 10 y 350 solicitudes, incluidos fallos/reintentos/evaluadores/Ollama. Ledger independiente en `live/campaign-budget.json`. Los ledgers anteriores permanecen intactos. Reserva conservadora antes de cada envío HTTP/Botocore, incluso intentos fallidos; hooks activos hasta salida del proceso. La reserva no es una factura.

Se mantienen modelos/endpoints de la campaña anterior: OpenAI gpt-4.1-mini; Bedrock Qwen3-32B en us-east-2; Ollama local Qwen3 4B; cloud Gemma4:31b. Cloud usa el slug canónico registrado del mismo modelo. No se descargan ni sustituyen modelos.

Matriz de 12 combinaciones: pilotos, controles negativos y challenge compuesto con dos actores, Tools, Context, lineage, Memory, Environment y Eval. Bedrock usa `required`; otros proveedores `auto`, explícitamente. Extras: nulabilidad exacta en tres frameworks Bedrock, System mixto de tres actores en cuatro rutas y controlador Studio/Bedrock en tres frameworks. Ninguna prueba aislada acredita toda la API o toda la UI.

Fuentes de referencia para reservas: [OpenAI](https://developers.openai.com/api/docs/models/gpt-4.1-mini), [Bedrock](https://aws.amazon.com/bedrock/pricing/), [Ollama](https://ollama.com/pricing). Se reservan tarifas conservadoras superiores para Bedrock/cloud; sin descuentos de caché, con margen y framing.

### Casos originales repetidos

- Strands + Bedrock pasó la composición completa con `required`: Tools, dos actores, decisiones, Environment, Memory, lineage y Eval; no se declara equivalente a la política `auto` histórica.
- El System mixto native/OpenAI Agents/Strands pasó en OpenAI, Bedrock, Ollama local y Ollama cloud, con salida exacta `value=45`, trail de los tres actores y validación. Esto aporta la repetición que faltaba para cloud.
- Studio + Bedrock pasó el cálculo observado `7*6=42` en los tres frameworks. Es aceptación del controlador para ese caso, no certificación completa de UI/streaming.
- La nulabilidad falló con `auto` en los tres frameworks; los contratos rechazaron la falta de evidencia obligatoria. Se preservan los intentos en `live/extras/`.
- Se repitió con `required`, mismos modelo/entrada/oráculo, y falló en los tres: la Tool fue solicitada, pero la segunda fila llegó sin `amount`. Una tercera serie con captura de petición/respuesta conserva esquema estricto, selección y ToolUse recibido en `live/null-wire-*.json`. No se relaja ni repara silenciosamente el dato.

### Bloqueo `amount:null`: evidencia más precisa

La captura en el límite Botocore muestra `toolSpec.strict=true`, `toolChoice.any`, Row con `required=[id,amount]` y `amount` admitiendo integer/null. La respuesta de servicio ya carece de la clave en la segunda fila, antes del despacho local. No hay una proyección de Agentic Systems que quite el nulo en ese punto. Las pruebas del parser existentes conservan nulos presentes.

La documentación de [structured outputs de Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html) describe validación estricta de nombres y argumentos y admite nulabilidad. El resultado observado no cumple el esquema enviado. No podemos separar, con esta evidencia, generación del modelo y transformación interna del servicio/SDK. Los request IDs se conservan para una investigación del proveedor; no se ha enviado un ticket ni compartido información fuera de esta campaña.

El contrato local funciona: no se ejecuta el cuerpo con argumentos inválidos y no se acepta el resultado inventado posteriormente por el modelo. Este caso permanece fallido: no debe anunciarse como corregido por tener `strict=true` ni por pasar los mocks offline. No se cambió a IAM ni a otro modelo. No se añaden defaults ni se reconstruye la clave ausente.

La decisión siguiente es investigar una representación de esquema equivalente que el servicio respete, o una ejecución determinista sobre la entrada original mediante referencias explícitas. Son alternativas de trabajo futuro, no sustitutos del caso fallido ni cambios incluidos en este wheel.

### Contabilidad por caso

Matriz y extras compartieron ledger y algunos trabajadores coincidieron temporalmente. Los campos históricos `requests` calculados como diferencia de ventanas globales pueden incluir solicitudes de otros trabajadores. `summary.json` usa fase y ventana para atribuirlas; `campaign-budget.json` sigue siendo el contador global autoritativo, reservado antes del envío. No se resta ni reembolsa consumo de intentos fallidos. Las cifras finales se generan tras terminar todos los trabajadores.

## Fuera de alcance

vLLM GPU, AWS IAM y ADA IAM siguen pendientes de sus entornos. CI remota, publicación y certificación completa de UI/MCP/A2A no forman parte de esta campaña.

## Reproducción

Regresiones canónicas: `tests/learning214/test_provider_policy_regressions.py`, `test_studio_lab_packaging.py`, `test_bedrock_null_input.py` y `test_bedrock_strict_tools.py`. Runner offline: `scripts/test_offline_214.py`; source con `--source`, instalado con `PYTHONPATH` apuntando al directorio registrado en installation.json. El guard prohíbe red de aplicación y subprocesses; los sockets/procesos del kernel se preparan fuera de él.

La evidencia live conserva RunResult serializable, human_results y linaje en los extras; la matriz conserva los resultados anidados y sus oráculos. `live/run.py`, `supplement.py`, `supplement_required.py`, `null_wire_worker.py`, `studio_worker.py` y `extras.py` registran los perfiles usados. No volver a ejecutar sus llamadas sin comprobar saldo, estado de servicios y bytes: cada intento consume presupuesto, aunque falle.
