# Bedrock: campo obligatorio nullable · corrección local, build 03

**Corregida la petición y validada offline. El caso real sigue pendiente.**
SDK 2.1.4.dev5, build local 03, sin publicar. No se ejecutó inferencia ni se
alteraron los límites o el historial de la campaña. No cambia la gramática
pública; el usuario no necesita otro constructor, parámetro o bandera.

## Hallazgo y límite de la conclusión

El caso original contiene:

```json
{"rows":[{"id":1,"amount":10},{"id":1,"amount":null}]}
```

Row.amount es obligatorio y acepta entero o null; no tiene valor por defecto.
La [captura de diagnóstico anterior](../../release-followup/20261026T041342447431-bedrock-diagnostic/results.json)
contiene el nulo en el prompt y required/anyOf-null en el esquema. La primera
respuesta del servicio ya trae la segunda fila como {"id":1}, sin amount.
La [repetición dev5](../bedrock-recheck.md) volvió a observar el mismo error
en native, OpenAI Agents y Strands.

La omisión ocurre antes del validador local. Esa evidencia no permite
separar el comportamiento del modelo de la transformación interna del servicio
Bedrock. Botocore y los adaptadores conservan un null cuando efectivamente
está presente. No se atribuye la omisión a Pydantic.

Encontramos una carencia corregible en nuestra petición: el esquema se enviaba
sin toolSpec.strict. Declarar un esquema como descripción de una Tool no
equivale a exigir decodificación restringida. AWS documenta
[strict tool use](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)
y marca [Qwen3 32B como compatible en bedrock-runtime](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-qwen-qwen3-32b.html).
La disponibilidad efectiva en la cuenta y la conservación del dato deben
comprobarse con el piloto; no se deducen de una respuesta simulada.

## Qué cambió

- Una proyección interna compartida activa strict para qwen.qwen3-32b-v1:0
  cuando el esquema original pertenece a un subconjunto conservador de AWS.
  Native y OpenAI Agents pasan por el mismo Converse; Strands aplica la misma
  proyección después de formatear su petición real.
- El esquema se copia sin modificar required, anyOf, referencias, defaults,
  restricciones o valores. Se reconocen objetos cerrados, arrays, referencias
  locales no recursivas y tipos básicos, incluido null. Se acotan opcionales
  y uniones. No se confunde el Tool.strict de salidas locales con esta
  capacidad del transporte.
- Un esquema abierto o no representable conserva íntegramente su contrato y
  validación local; no se borra una restricción para habilitar strict. No se
  certifica decodificación restringida en ese caso ni para otros modelos.
  Una elección strict explícita del SDK se conserva. Un rechazo del servicio
  no provoca una repetición automática con un esquema más débil.
- La lectura del cliente Bedrock permite al menos 120 segundos. AWS advierte
  que compilar un esquema nuevo puede tardar unos 90 segundos. El scheduler
  sigue aplicando el plazo del usuario; el próximo piloto necesitará plazos
  coordinados superiores a la compilación, sin repetir por un timeout corto.
- Las dependencias opcionales Bedrock exigen Boto3/Botocore >=1.43.38, versión
  cuyo modelo de servicio y serializador aceptaron strict en las pruebas.
  No se afirma que sea la primera versión que añadió la capacidad.
- La serialización real detectó además que Strands recibía instrucciones
  ausentes como texto vacío, inválido en Converse. Ahora se representa su
  ausencia con None.

| Input | Proceso comprobado offline | Output |
| --- | --- | --- |
| Segunda fila con amount:null | Esquema obligatorio nullable, strict en la petición, SDK real y validación de Tool | Dos filas, un importe ausente; el null se conserva en los eventos |
| Segunda fila sin amount | Validación del mismo contrato, antes del cuerpo de la Tool | RunResult fallido, error Field required, cero efectos de negocio |
| amount=0 | Validación estricta del entero | Sigue siendo 0; no se convierte en null |
| amount="null" | Validación estricta del tipo | Rechazado; no se convierte una cadena a null |
| Servicio rechaza strict | Se conserva el error original | Una sola llamada simulada, sin degradar el esquema |

Strict protege la forma del argumento, no su veracidad. La aceptación real
seguirá exigiendo igualdad exacta entre los argumentos y la entrada congelada,
resultado de negocio exacto, eventos, invariantes y linaje serializables.
Un amount inventado que satisfaga el tipo también bloquearía esa aceptación.

## Pruebas y artefacto

- **319 pruebas aprobadas**, cero fallos, errores o pruebas omitidas.
  Incluyen **20 regresiones nuevas** y las tres regresiones previas del nulo.
- Los tres SDKs reales recorren los casos positivo y negativo con un
  transporte simulado. Se valida y serializa la petición con Botocore real.
  Se comprueban también campos opcionales, no mutación del esquema,
  modelos no verificados, recursión, límites y conservación de decisiones SDK.
- El bloqueo de red/inferencia registró cero intentos de aplicación.
  Las llamadas simuladas de los SDKs no son solicitudes reales ni aceptación
  de un proveedor. Se conservaron los intentos offline anteriores.
- Análisis estático de los archivos modificados y git diff --check aprobados.
  Hay 13 avisos de deprecación de dependencias, sin fallos de ejecución.
- Wheel instalado sin modo editable en una carpeta temporal fuera del
  repositorio. Verificados RECORD del wheel, hashes, contenido del sdist y
  correspondencia entre código fuente, wheel e instalación.
- Los notebooks/examples y sus campañas anteriores conservan su evidencia;
  este trabajo no repitió todos los notebooks ni transfiere sus PASS al nuevo
  hash.

[Resultado estructurado](summary.json) · [JUnit](offline-junit.xml) ·
[Registro de pruebas](offline-tests.log) ·
[Wheel nuevo](../builds/03/agentic_systems-2.1.4.dev5-py3-none-any.whl) ·
[Hashes](../builds/03/hashes.json).

Wheel SHA-256:
```text
df328e52d7a2660d7b29ce45a40c689766ce99196c02d5672930dd5663bbde34
```

Build 02 y su evidencia permanecen intactos. El nuevo build mantiene la
versión de desarrollo local y tiene bytes y SHA-256 distintos. No se ha
sobrescrito ninguna distribución publicada ni se ha sellado una estable.
La aceptación de build 02 no certifica build 03.

## Presupuesto de cierre: propuesta, no autorización

El contador permanece en **148/150 solicitudes**, con **USD 0.875040 de reserva
acumulada** sobre un máximo de USD 5. Quedan dos solicitudes y USD 4.124960
de reserva. Es una contabilidad conservadora, no la factura del proveedor.
El hash del ledger no cambió:
```text
6ce1ae54e97e11835598312e56ca403ca7b267478a99ce1bc5c93a0bdbd5b9e6
```

Hay dos alcances:

| Alcance | Plan nominal | Margen | Cambio propuesto del límite |
| --- | --- | --- | --- |
| Corrección y pendientes afectados | 48 solicitudes | 12 | 150 → 210 totales, manteniendo USD 5 |
| Candidata completa, recomendado | 158 solicitudes | 44 disponibles desde el contador actual | 150 → 350 totales, manteniendo USD 5 |

El alcance acotado incluye un piloto native (2), dos pasadas del nulo en los
tres actores (12), Studio/Bedrock en los tres (9), interoperabilidad cloud (6),
interoperabilidad Bedrock (6), y regresión básica/reembolso/MCP/A2A Bedrock (13).
La interoperabilidad Bedrock no tiene una fila en la matriz actual de build
02; se detectó esa laguna al calcular el cierre y se incluye expresamente.

La candidata completa repite el perfil de aceptación sobre los nuevos bytes:

| Familia | Escenarios | Solicitudes nominales |
| --- | ---: | ---: |
| Notebook básico, cuatro destinos × tres actores | 12 | 24 |
| Handoff OpenAI Agents | 1 | 2 |
| Reembolso con pausa y reanudación | 12 | 12 |
| Studio, controlador con historial y calculadora | 12 | 36 |
| MCP y A2A con Strands | 8 | 16 |
| Tres frameworks juntos, cuatro destinos | 4 | 24 |
| Casos de negocio congelados y distribuidos | 15 | 30 |
| Nulo obligatorio Bedrock × tres actores | 3 | 6 |
| Segunda pasada del nulo | 3 | 6 |
| Piloto separado de aceptación | 1 | 2 |
| **Total nominal** | **71 ejecuciones** | **158** |

Desde 148 hasta el tope propuesto 350 quedarían 202 solicitudes:
158 previstas y 44 de margen. El dinero disponible parece suficiente según
las reservas observadas; no se garantiza un coste final ni se aumenta el
tope de USD 5. Se detendrá al alcanzar cualquiera de ambos límites. Fallos,
reintentos, evaluadores, Ollama y respuestas posteriores a un timeout cuentan.
No se crea un ledger nuevo ni se borra el historial.

La interoperabilidad Ollama cloud sigue fallida por salida final vacía y
requiere diagnóstico propio; reservar una repetición no promete que se
arregle. El siguiente orden será cerrar su diagnóstico offline, congelar
los bytes finales, piloto Bedrock, aceptación del nulo y después la matriz.
Si ese diagnóstico requiere cambiar el SDK, se generará otro build y la
campaña completa se vinculará a ese hash, no a build 03.
Un fallo obligatorio detendrá la aceptación; no se repite hasta ocultarlo.

vLLM GPU sigue aplazado por indicación del usuario; AWS IAM y ADA IAM
requieren sus entornos. La propuesta no alquila GPU, no cubre servicios
externos nuevos y no publica. CI Python 3.10–3.14, workflows de la nueva API,
entregables coherentes y la aceptación estable siguen siendo condiciones
independientes antes del release.
