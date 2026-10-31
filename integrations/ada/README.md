# Complemento AWS/ADA · 2.1.4.dev8

Distribución independiente y opcional, todavía sin publicar. No se instala con
el SDK ni con su extra all. Usa el mismo Agent/System/Graph y el runtime Bedrock
existente; no añade otra gramática. No hay un extra [ada] duplicado de [bedrock].

Instala primero el wheel SDK dev8 y luego el wheel agentic-systems-ada dev8 con
sus dependencias disponibles en tu índice o wheelhouse. Para trabajar desde este
checkout después de instalar el SDK:

```console
python -m pip install --no-deps --no-build-isolation ./integrations/ada
agentic-systems-ada doctor
```

```python
import agentic_systems as toolkit
import agentic_systems_ada as ada

# supplied_session es la sesión que ya preparó tu plataforma AWS/ADA.
report = ada.diagnose(session=supplied_session)
aws = toolkit.runtime(
    provider="bedrock-runtime", model="modelo_habilitado",
    session=supplied_session,
)
```

diagnose no consulta credenciales, STS ni metadatos, y no modifica variables.
No certifica la identidad, acceso al modelo ni ADA. Una pareja estática sin token
es ambigua; no se borra automáticamente. Corregir la cadena de autenticación es
una operación de administración explícita fuera de la ejecución de los agentes.

Una sesión prestada selecciona IAM y su región; api_key/endpoint contradictorios
se rechazan. Un bearer global no desplaza esa selección. Las invocaciones del
toolkit que usan la misma sesión se serializan; el uso concurrente externo sigue
siendo responsabilidad del propietario. No se cierra la sesión ni se serializa
en Context, estado, Memory, resultados o configuración JSON. No se admite mover
la sesión prestada a otro proceso.

La validación offline usa transportes simulados con los tres SDKs. AWS IAM y ADA
IAM reales siguen pendientes. El paquete no configura Artifactory, proxy, CA,
roles ni credenciales, y no incluye ADA Studio ni wallet.
