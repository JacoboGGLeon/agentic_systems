# Ollama native: conexión por actor

Corrección local de 2.1.4.dev8. La fase offline de este informe no consumió
inferencia. La [repetición online posterior](live/REPORT.md), autorizada por
USD 2/70 solicitudes, pasó los perfiles sync/arun y el notebook original:
58 solicitudes, USD 0.493025 reservados. No se publica.

## Resultado final offline

**544 pruebas satisfactorias** sobre el wheel instalado fuera del checkout;
cero fallos/errores y cero intentos de red de aplicación. Hay 14 avisos de
dependencias/importación. `final-suite.xml` y `final-suite.log` conservan la
suite completa final. Las 13 regresiones específicas también pasan separadas
en `installed-unit-final.xml`.

Cobertura del núcleo: 1965 statements, 100%. Esta configuración excluye `_engine`
y templates: no es una afirmación de cobertura completa del adaptador privado.
Lint y escaneo de claves locales pasan. El ledger permanece byte por byte igual,
con 344 solicitudes; no se han ejecutado pruebas online ni transferido aceptación
live del wheel anterior.

## Cambio

El actor native usaba siempre `OLLAMA_BASE_URL` y `OLLAMA_API_KEY`. Ahora el
proveedor resuelve endpoint y clave desde `agent.runtime_config` en cada
invocación; si no existe, considera la configuración del System propietario.
Solo los campos no declarados toman los valores del entorno y, finalmente,
los defaults existentes. SecretStr se revela únicamente para construir el cliente.
Una clave explícitamente vacía no se sustituye silenciosamente por otra.

La configuración y clientes de un actor no se almacenan como valores globales
ni se reutilizan en el siguiente actor. `run` y `arun` aplican la misma regla.
Se cierran los clientes creados internamente incluso ante error; los clientes
inyectados por el llamador siguen siendo responsabilidad de este.

No cambia la API pública. Para mezclar local/cloud, declarar las dos conexiones:

```python
local = toolkit.runtime(
    provider="ollama-runtime", model="qwen3:4b-instruct-2507-q4_K_M",
    endpoint="http://127.0.0.1:11434/v1", api_key="ollama-local",
)
cloud = toolkit.runtime(
    provider="ollama-runtime", model="gemma4:31b",
    endpoint="https://ollama.com/v1", api_key=os.environ["OLLAMA_API_KEY"],
)
```

El ejemplo necesita los imports habituales de toolkit y os. Las claves no van en
State/Context/Memory ni en los artefactos. Si se omite api_key, se mantiene el
fallback del entorno; declarar la clave local evita enviar una clave cloud al
servidor local. No se altera el entorno para alternar conexiones.

## Regresiones

`tests/current/test_ollama_connections.py`: 13 casos offline.

- System con dos actores native local/cloud, secuenciales y paralelos, run/arun.
- Dos ejecuciones del mismo compilado, ocho despachos HTTP simulados por caso.
- SDK OpenAI real con MockTransport: URL, autorización y modelo exactos,
  Tools observadas, datos de negocio y ausencia de claves en RunResult.
- Mismo proveedor reutilizado con tres invocaciones concurrentes, sync y async.
- Ruta async del proveedor probada directamente con transporte SDK real simulado;
  no se confunde System.arun con una prueba de ese método privado del proveedor.
- Prioridad por campo, SecretStr, defaults, System propietario, clave vacía,
  clientes inyectados y cierre normal/ante fallos. Variables Ollama invariantes.

El caso System secuencial falla con el wheel anterior y pasa con el nuevo;
`old-wheel-red.*` conserva la demostración. Su error adicional de teardown
documenta clientes internos sin cerrar en la implementación anterior.

La primera versión de la prueba no declaraba output_schema: native conservaba
el JSON como texto y el grafo no recibía los canales de negocio. Se añadieron
contratos de salida explícitos; no se relajaron los asserts esperados.
Se preservan los logs de todos los intentos.

## Artefacto

Wheel privado en build01/dist, no editable, instalado fuera del repositorio.
SHA-256: `2fd51f0ade843d9d8d4ef19bfbfd08d5f2d116947a5fc0b2cbed5c4f8dff6b60`.
Los 117 archivos de payload coinciden entre source, wheel e instalación.
`installation.json` y `artifact-verification.json` registran rutas y verificación.
Studio y el diagnóstico ADA instalados son los wheels locales anteriores, sin
modificaciones ni llamadas a IAM/ADA. La aceptación live de bytes anteriores
no se transfiere a este wheel.

## Presupuesto propuesto para repetir online

El contador conserva 344/350 solicitudes y USD 3.255425 reservados: quedan seis.
No se consumen en esta tarea. La reserva es un control conservador, no factura.

| Perfil | Solicitudes nominales |
|---|---:|
| Pilotos local y cloud | 2 |
| Dos pasadas del System local/native + cloud/native, sync | 8 |
| Dos pasadas del mismo System, async | 8 |
| Notebook financiero original con local/native, cuatro proveedores y tres frameworks; operación + 2 episodios + 2 Eval | 40 |
| Total | 58 |

**Recomendación: campaña nueva de USD 2 y 70 solicitudes.** Deja 12 solicitudes
para fallos/reintentos o variación SDK. Estimación basada en las reservas observadas
en el notebook anterior (40 solicitudes: USD 0.411877), no garantía de coste.
Congelar modelos/entradas/oráculos, recalcular reservas y detener al primer tope.
Si fallan los pilotos, no gastar el saldo en la composición. No ejecutar online
hasta disponer de autorización para esa campaña; este informe no la concede.

Para repetir solo la regresión específica, sin notebook: 18 nominales; propondría
USD 1 y 24 solicitudes. Eso no acredita aceptación amplia del nuevo wheel.
Una aceptación completa de la matriz y escenarios previos requiere plan aparte;
como referencia, hasta USD 10 y 350 solicitudes, sin prometer cerrar amount:null.

## Pendientes

La repetición live específica con los nuevos bytes ya pasó; véase el informe
online enlazado al inicio. El notebook anterior con Strands/local
sigue siendo evidencia histórica válida de aquellos bytes, pero no es el ensayo
native corregido. No se reescriben sus outputs como si hubiesen sido repetidos.
amount:null Bedrock/Qwen, IAM/ADA y vLLM GPU no se corrigen en este trabajo.
