# Tutorial Quality Standard

Status: release gate for Agentic Systems 1.1.

Los notebooks son la demostración ejecutable del producto. No son una segunda
implementación, una colección de snippets ni una forma de ocultar lógica de
dominio que la API pública no puede expresar.

## Contrato De Aprendizaje

Cada notebook debe permitir que una persona responda, al terminar:

1. Qué problema resuelve esta parte de la API.
2. Qué objeto crea y quién es su owner.
3. Qué parámetros cambian el comportamiento.
4. Qué resultado y evidencia produce.
5. Qué puede fallar, degradarse o requerir un servicio externo.
6. Cómo reutilizar el mismo patrón fuera del notebook.

## Ruta Pública Canónica

Todo notebook importa una sola fachada:

```python
import agentic_systems as toolkit
```

La ruta pedagógica de construcción es:

```python
toolkit.tool(...)
toolkit.skill(...)
toolkit.agent(...)
toolkit.system(...)
toolkit.graph(...)
toolkit.environment(...)
toolkit.eval(...)
```

Las clases públicas permanecen disponibles para typing, extensión y control
avanzado, pero los notebooks deben preferir estas factories cuando construyen
los conceptos centrales.

La agnosticidad es obligatoria: Provider, Framework y estrategia se seleccionan
mediante rutas y registros públicos. Un valor fijo solo se admite como fallback
reproducible y debe quedar declarado, nunca como lógica de dominio escondida.

## API Antes Que Código Local

Un notebook puede declarar datos, funciones de dominio, callbacks y fixtures
pequeños para hacer observable una conducta. No debe:

- reimplementar una capacidad que ya ofrece `toolkit`;
- importar módulos internos de `agentic_systems`;
- depender de código escondido en `examples/` o en otro tutorial;
- usar mocks o clases `Fake*` para afirmar que un Provider real se ejecutó;
- sustituir contratos, resultados, lineage, environments o evals por
  diccionarios fabricados cuando existe una API pública equivalente;
- reportar un skip de infraestructura como ejecución exitosa.

Los inputs de demostración deben estar nombrados y ser fáciles de cambiar. Un
ejemplo determinista es válido cuando enseña la API; deja de serlo cuando toda
la conducta importante está hardcodeada fuera de la librería.

## Estructura Esperada

Cada notebook contiene:

1. objetivo o historia de usuario;
2. parámetros editables;
3. modelo mental y ownership;
4. construcción mediante `toolkit`;
5. ejecución o skip explícito;
6. resultado humano primero y evidencia estructurada después;
7. al menos un límite, fallo o riesgo;
8. inventario final `api_coverage`.

## Contrato Run All

Un tutorial debe funcionar de arriba abajo con **Run All**. No puede depender de
que el usuario conozca una celda de activación, ejecute un bloque fuera de orden
o reconstruya manualmente estado intermedio.

Para notebooks con Providers externos:

- live está habilitado por defecto cuando el preflight confirma readiness;
- readiness se observa mediante API pública y variables del entorno, no mediante
  imports directos del SDK;
- `RUN_*_LIVE=0` es un opt-out explícito para demos, CI o ejecución offline;
- un Provider configurado recorre `runtime -> system -> agent -> RunResult`;
- infraestructura ausente produce un skip accionable, no un resultado fabricado;
- una llamada intentada que falla conserva el error real del Provider.

Después de instalar y configurar la frontera externa, **Run All debe ser
suficiente**.

## Evidencia De Release

El gate automatizado valida estructura, imports, compilación, API pública y
outputs limpios. Ejecuta desde kernels limpios los 13 notebooks deterministas y
valida estáticamente los 5 notebooks de Provider. Las llamadas live solo se
afirman cuando existe evidencia explícita de esa ejecución.
