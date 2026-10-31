# AWS y ADA: antecedentes y propuesta para 2.1.4

Documento histórico del diseño previo a dev8. La implementación y sus límites
vigentes están en [AWS y ADA opcional](ADA_214.md). Las afirmaciones siguientes
de «todavía no implementado» describen el momento de esta propuesta, no dev8.

**Diseño, no implementación.** No existe todavía el extra [ada], el paquete
agentic-systems-ada ni el argumento público session= en la revisión dev7.
No se hizo inferencia, STS ni reparación del entorno durante esta auditoría.

## Qué existía en 2.1.0, 2.1.1 y 2.1.2

Se leyeron los tags locales v2.1.0/v2.1.1/v2.1.2. Los módulos utils.py,
providers/bedrock_runtime.py y providers/bedrock/identity.py tienen el mismo
contenido en los tres tags. El archivo Strands cambió en otras capacidades,
pero conserva las asignaciones de sesión/región/autenticación y boto_session
examinadas. Los hashes y las asignaciones están en
[findings.json](../revisions/2.1.4/pre-freeze-audit/01/findings.json).

| Pieza histórica | Función real | Situación dev7 |
|---|---|---|
| aws_environment_snapshot | Inspecciona variables AWS; por defecto SET/None. El modo include_values podía devolver valores crudos. | Existe bajo _engine/utils.py, no es export público. No reexponer valores de credenciales. |
| boto3_session_snapshot | Construye una Session, consulta su proveedor y describe región/método/modo IAM o bearer. | Interno; no forma parte de la gramática vigente. get_credentials puede activar la cadena de proveedores: no llamarlo offline sin un doble controlado. |
| repair_ada_credential_chain | Detecta una posible pareja estática que eclipsa el rol; solo con force=True elimina variables, incluidos perfil y token. | Interno y fuera de la API. No activarlo automáticamente ni suponer que la ausencia de session token invalida una clave de larga duración. |
| BedrockRuntime.session | El runtime construye una boto3.Session y crea con ella clientes Bedrock Runtime, Bedrock y, en IAM, STS. | Se conserva internamente. Cada construcción puede crear una sesión nueva. |
| Adaptador Strands | Entrega runtime.session a BedrockModel mediante boto_session y evita pasar simultáneamente region_name. | Se conserva bajo _engine/integrations/adapters/strands.py. |
| whoami / model_availability | Identidad STS en IAM y metadatos/disponibilidad; bearer no sirve para GetCallerIdentity. | Internos; comprobación de identidad no equivale a inferencia ni a éxito de negocio. |
| Bundle ADA offline | Entrega wheel, aplicación/materiales y evidencia para entorno restringido. | Un bundle no es un runtime diferente ni un extra de pip. Debe regenerarse y validarse por separado. |

En ninguno de los tres pyproject.toml examinados existe una entrada ada en extras.
El constructor BedrockRuntime tampoco recibe una Session del usuario: la crea
internamente. La prueba histórica tests/unit/test_framework_materialization.py
exige `bedrock_calls["boto_session"] is session`. Eso demuestra conservación de
identidad entre runtime y adaptador Strands, no herencia pública entre cualquier
runtime ni inyección de una sesión corporativa ya preparada.

## Qué conviene incorporar y dónde

### Núcleo AWS reutilizable

Proponer un único argumento opcional session= en el runtime Bedrock existente;
no crear AdaRuntime ni otra forma de construir Agents/Systems.

```python
import agentic_systems as toolkit

# Propuesta futura: session= AÚN NO está implementado en dev7.
aws = toolkit.runtime(
    provider="bedrock-runtime",
    model="modelo_habilitado_en_tu_region",
    session=corporate_session,
)
```

corporate_session es una Session ya preparada por la plataforma o por boto3,
no una bolsa de claves. Esta capacidad general beneficia a AWS, SageMaker y ADA.
Debe conservar el mecanismo de credenciales/renovación que ya ofrezca la sesión;
no congelar access key/secret/token para copiarlos a otro runtime. Boto3 documenta
que los clientes de una sesión comparten las credenciales temporales de su
proveedor y su renovación cuando ese proveedor la soporta.
[Credenciales Boto3](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html).

Contratos pendientes de implementar/probar:

- Sesión opcional solo para Bedrock; validación sin importar boto3 si no se usa.
- Rechazar combinaciones contradictorias de sesión, api_key y región. Definir la
  precedencia frente al bearer del entorno y comprobar el modo observado.
- Mantener la sesión como recurso privado/excluido de repr/serialización. No meterla
  en Context, estado, Memory ni evidencia. Una configuración JSON no restaura
  automáticamente una conexión viva.
- Native, OpenAI Agents y Strands usan la misma ruta de autenticación; ningún
  adaptador reconstruye credenciales ni cambia de región en silencio.
- Lifecycle/propiedad explícitos: no cerrar recursos externos arbitrariamente ni
  tratar una sesión como transportable entre procesos.
- Diseñar el ámbito de concurrencia antes de declarar soporte paralelo. AWS dice
  que Session no es thread-safe; no prometer una única Session global compartida
  por todos los workers. La identidad histórica probada en una materialización
  no es una garantía universal de concurrencia.
  [Sesiones y concurrencia](https://docs.aws.amazon.com/boto3/latest/guide/session.html).

### Complemento ADA opcional

Recomiendo una distribución independiente agentic-systems-ada, instalable solo
donde se necesita. Su API pequeña de diagnóstico y validación empresarial viviría
en agentic_systems_ada, sin añadir constructores al toolkit principal.

Podría agrupar diagnóstico seguro de configuración, comprobaciones explícitas de
identidad/acceso, perfil de aceptación ADA y material offline con hashes. No debe
asumir que conoce CA, proxy, índice Artifactory o roles: son configuración del
entorno que se documentará y validará allí. No cambia Agents, Systems o Graph.

La reparación de variables debe seguir siendo una operación explícita, con vista
previa y alcance documentado; preferir diagnóstico y corrección de configuración
a mutar todo el entorno del proceso durante una ejecución concurrente.

Un extra [ada] es una lista de dependencias opcionales; no es otra compilación
del wheel ni instala credenciales. Podría ser un atajo hacia el complemento cuando
este exista. Como [bedrock] ya instala boto3/botocore, añadir ahora un [ada] idéntico
solo duplicaría un nombre, sin independencia real.
[Extras en PyPA](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#dependencies-and-requirements).

No incluir el complemento en [all] ni declarar ADA validada por instalarlo. Studio
para ADA y su futura wallet son otro entregable, con contrato y validación propios.

## Validación y entrega

1. Primero probar la inyección general offline con sesiones/clientes dobles:
   propagación, conflictos, ausencia de secretos, renovación del proveedor,
   errores, cierre y concurrencia dentro del ámbito que se declare soportado.
2. Probar el mismo negocio y evidencia en native/OpenAI Agents/Strands, evitando
   usar un fixture como prueba de IAM real.
3. Separar IAM AWS, IAM ADA y bearer Bedrock. La aceptación real exige entorno,
   rol y modelo habilitados; metadata/configuración no lo demuestra.
4. Crear el complemento, su matriz de compatibilidad, dependencias y wheelhouse
   reproducible para las versiones/plataformas objetivo. ADA/Artifactory valida
   los artefactos que efectivamente tiene disponibles, con sus hashes.
5. Si se incluye session= en 2.1.4, cambia el SDK: construir nuevos bytes y repetir
   su aceptación. Si el complemento no llega a validarse, entregarlo después de
   forma independiente y mantener la ruta ADA explícitamente pendiente.
