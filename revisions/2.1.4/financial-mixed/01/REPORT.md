# Sistema financiero explícito: Python y proveedores mezclados

SDK local 2.1.4.dev8 corregido; wheel SHA-256
`3fe02c467f5dd71855dfbdce95029393b893c773211bf6307700cb9e243238dd`,
instalado fuera del checkout. No se modifica el SDK ni se publica.

## Resultado final

Python y el perfil mixto final pasaron todas las celdas en kernels limpios.
El hash de código del notebook es el mismo en ambas ejecuciones:
`2815c0ccfd3a85eeb82b7a69185d0c422fb3ca6e0ec7b984bf67ee5e019e0ac4`.
Los outputs de negocio y el resumen de Environment/Eval coinciden. Los IDs,
trazas, tiempos y consumos son distintos y se conservan, no se comparan como
si fueran datos de negocio idénticos. Cada perfil captura 20 Context recibidos.

El perfil mixto registra los cuatro modelos y los tres adaptadores SDK realmente
usados; `verify.py` lo comprueba junto con igualdad de negocio y escaneo de secretos.
Las salidas visibles están en los dos notebooks de examples/financial_mixed/.

Python: cero inferencia. Mixed final: 40 solicitudes, USD 0.411877 reservados.
Primer intento fallido: cuatro solicitudes, USD 0.035893 reservados. Total de esta
tarea: **44 solicitudes y USD 0.447770 de reserva conservadora**, no factura.
Campaña acumulada: **344/350 solicitudes y USD 3.255425/10 reservados**. Quedan
seis solicitudes. Todos los kernels terminaron con el medidor activo hasta su cierre.
[Resumen estructurado](summary.json).

## Aplicación

Todos los contratos y grafos están visibles en el notebook. Tools Pydantic
validan, calculan y verifican; Skills declaran capacidades; Agents tienen actores
y grafos propios; System coordina cuatro actores y una decisión. Context conserva
política y fuentes; el auditor usa linaje actual y episodios de Memory.
Environment procesa dos registros y calcula recompensa explícita; Eval clona
Memory por caso y mantiene intacta la exterior. No hay entrenamiento RL.

| Caso | Input | Proceso | Output esperado |
|---|---|---|---|
| Operación | SINGLE, 15000 | fee 1%, límite 10000 | fee=150, review, pending_review |
| Episodio 1 | PAY-001, 5000 | fee + linaje + Memory | fee=50, approve, approved |
| Episodio 2 | mismo pago | consulta aprobación histórica | review_duplicate, pending_review |
| Eval | EVAL-001 dos veces | casos aislados | dos aprobaciones, Memory exterior intacta |

Las tres raíces RunResult incluyen human_results, linaje serializable y Context
recibidos. Las verificaciones exigen invariantes, roundtrip JSON, resultados
exactos y estado sin trazas infladas. Las comprobaciones financieras son
deterministas; los modelos seleccionan Tools y devuelven sus resultados.

## Configuración mixta final

Comisión: OpenAI/native. Auditoría: Bedrock Qwen3-32B/Strands.
Verificación local: Ollama local Qwen3 4B/Strands. Final:
Ollama cloud Gemma4:31b/OpenAI Agents. Graph es LangGraph en todos los casos.
Python ejecuta la misma composición con cuatro actores Python/native.

## Intentos y alcance

La primera versión Python pasó sin inferencia. El primer mixed falló tras cuatro
solicitudes efectivas (OpenAI y Bedrock): el actor native de Ollama lee su endpoint
del entorno global en vez de la conexión explícita. El medidor rechazó la ruta
incompatible antes de transporte; el SDK mostró Connection error. No se ejecutó
la Tool local ni se alcanzó cloud. No se presenta como fallo de disponibilidad
de Ollama ni como éxito de la mezcla original.

Se preserva el fallo con notebook parcial y result.json. La limitación se observa
en `providers/ollama_runtime.py`: `_client_from_environment` usa `_ollama_base_url()`.
No se modifica ese SDK ni se oculta el cambio: la mezcla final elige Strands para
la conexión local. Se repitió Python y después el perfil mixto final.

El runner `execute.py` prepara únicamente instalación, entorno, kernel, guard y
presupuesto. No construye el sistema. El perfil Python usa guard sin inferencia;
mixed mantiene el contador activo hasta cerrar el kernel. El contador es el mismo
autorizado por USD 10/350 solicitudes; no se abre otra campaña ni se reinicia.
`budget-before-notebook.json` conserva las primeras 300 solicitudes con el mismo
SHA del manifiesto de la aceptación anterior. Los intentos nuevos se agregan.

Capturas por intento: `*-python/` y `*-mixed/`, con executed.ipynb, result.json y,
si termina, evidence.json. No se transfieren fondos. Los casos no sustituyen las
pruebas fallidas amount:null ni validan IAM/ADA/vLLM/Studio/handoffs/MCP/A2A.
