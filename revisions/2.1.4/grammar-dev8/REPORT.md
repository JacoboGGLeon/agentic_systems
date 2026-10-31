# Cierre offline · Agentic Systems 2.1.4.dev8

Estado: **validación local offline pasada; release estable pendiente**.
No se abrió PR, no se ejecutó CI remota, no se publicó y no hubo inferencia.
El árbol conserva trabajo previo sin commit; el commit base no representa por
sí solo estos cambios. [Fuentes y artefactos](delivery-build07/manifest.json) ·
[Vinculación de la evidencia](verification.json) · [Resumen](summary.json).

## Áreas de cierre

| Área | Resultado verificable | Límite |
|---|---|---|
| Source | Graph común, compile, Context/Memory, plazos, eventos y sesión AWS; 469 regresiones contra fuente | Python 3.14.2 local |
| API | 15 palabras propias y cinco objetos originales de LangGraph; firmas desde la instalación | Sin aliases de APIs anteriores; no se certifican todos los parámetros por mencionar una palabra |
| Tutorials | 22 notebooks en kernels nuevos | Solo perfil offline |
| Examples | Ocho notebooks y 58 entrypoints; 34 experimentos históricos adaptados conservan sus antecedentes | MCP/A2A mantiene perfil separado dev7; no se transfirió aceptación |
| Documentación y skill | Índices, estados, firmas, RunResults/Memory/linaje y skill dev8 alineados | Comprensión por usuarios nuevos aún no medida |
| CLI y scaffolder | Proyecto externo con espacios: app, example, tests, notebook y tres actores Python | doctor comprueba dependencias, no servicios |
| Pytests y calidad | 469 PASS instaladas, cero fallos/omisiones; Ruff, tres contratos de arquitectura y secretos | Cobertura de sentencias del núcleo 100%; motor privado y plantillas excluidos por política existente |

Pyright estricto: **nueve archivos actuales de esquemas/normalización, cero errores**.
El perfil antiguo apuntaba a módulos retirados y dos scripts históricos (225
diagnósticos); se conserva como antecedente y se migró a sus contratos vigentes.
No se afirma tipado estricto de toda la fachada ni de todos los SDK externos.
La primera prueba exploratoria usó rutas de configuración incorrectas y analizó
copias de staging; su salida no se considera diagnóstico de la candidata.

La suite genera 14 advertencias de dependencias/harness, conservadas en logs.
Los notebooks omiten **12 celdas live/local**, detalladas por archivo.
Los tres actores (native, OpenAI Agents y Strands) se ejecutan con Python
determinista. Las fixtures de transporte no prueban razonamiento ni IAM real.

La skill también pasó su [prueba funcional](skill-validation.json): ejemplo
integrado, scaffolder y tests del proyecto generado. Se corrigió la duplicación
de tests y de configuración pytest; el SDK conserva exactamente el mismo wheel.

## Artefactos

Wheel SDK probado: `14148af530c14660b888479f6a2eabb4ef1bf74637b7cc3244422f447b547e23`.
Se verificaron 122 hashes RECORD y 117 archivos de paquete coincidentes entre
fuente, instalación, wheel y sdist. SDK, Studio y ADA pasaron Twine estricto.
Los artefactos anteriores y los intentos fallidos de construcción se conservan.
Build06 falló por permisos del sandbox de pip; build07 se construyó offline en
su directorio nuevo. No se reemplazó ningún archivo publicado.

Los artefactos están en [delivery-build07/dist](delivery-build07/dist/).
El manifiesto de construcción necesita este verification.json: no equivale a
un manifiesto certificado de publicación. La matriz de Actions está preparada
para construir una vez y usar esos bytes en Python 3.10–3.14; aún no se ejecutó.

## AWS/ADA y antecedentes

En 2.1.0–2.1.2 existían snapshots/diagnóstico y reparación de la cadena AWS.
Bedrock construía una Session y Strands recibía esa misma sesión. No había
extra ada ni inyección pública de una sesión externa. La reparación global
del entorno no se trasladó automáticamente.

Dev8 añade session= al runtime Bedrock, sin otro constructor. Selecciona IAM,
rechaza conflictos, mantiene la sesión fuera de JSON/Context/Memory y no la
cierra. Las invocaciones que comparten el recurso se serializan dentro del
toolkit, sujetas al plazo; no se promete coordinación con usos externos.
El SDK ya no modifica IMDS globalmente. El paquete independiente ADA aporta
diagnóstico sin resolver credenciales ni llamar a STS/IMDS; no va incluido en all.
AWS IAM, ADA IAM y ADA Studio/wallet siguen pendientes.

## Evidencia de uso

[Inventario exhaustivo de notebooks](../../../docs/NOTEBOOK_INVENTORY_214.md) ·
[RunResults, human_results, Memory y linaje por archivo](../../../docs/RUNRESULTS_LINEAGE_214.md) ·
[API y firmas](../../../docs/API_214_SURFACE.md) ·
[Notebook de linaje que cambia decisiones](../../../examples/lineage_memory/01_lineage_memory_decisions.ipynb) ·
[Notebook de sesión AWS](../../../examples/aws_session/01_aws_session.ipynb).

## Antes de publicar

1. Revisar el diff final y preparar el PR, seleccionando fuentes/evidencia útiles;
   no añadir caches, backups ni todas las copias de staging al repositorio.
2. Exigir CI real en Python 3.10–3.14, incluido el análisis estricto migrado.
3. Acordar campaña online para este wheel. Ningún PASS live anterior se transfiere.
   Permanecen abiertos Bedrock/Qwen con amount:null, interoperabilidad Ollama
   cloud y Studio/Bedrock; consultar los casos originales, sin inventar valores.
4. Mantener vLLM GPU y AWS/ADA IAM pendientes hasta disponer de sus entornos.
   Repetir MCP/A2A y los controles Studio acordados para ampliar la aceptación.
5. Revisar numeración y notas de ruptura respecto a 2.1.3, congelar la candidata
   estable y promover sus mismos bytes por TestPyPI, PyPI y GitHub cuando se autorice.

Memory y continuaciones son locales al proceso: no hay recuperación durable,
rollback general ni API RL completa. No se presentan como implementados.
La campaña dev5 permanece intacta: 148/150 solicitudes y USD 0.875040 reservados;
quedan dos solicitudes, insuficientes para prometer la aceptación online completa.
