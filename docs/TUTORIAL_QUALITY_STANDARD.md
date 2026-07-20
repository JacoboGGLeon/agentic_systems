# Tutorial Quality Standard

Status: release gate for Agentic Systems 1.1.

Los notebooks son la demostracion ejecutable del producto. No son una segunda
implementacion, una coleccion de snippets ni una forma de ocultar logica de
dominio que la API publica no puede expresar.

## Contrato de aprendizaje

Cada notebook debe permitir que una persona responda, al terminar:

1. Que problema resuelve esta parte de la API.
2. Que objeto crea y quien es su owner.
3. Que parametros cambian el comportamiento.
4. Que resultado y evidencia produce.
5. Que puede fallar, degradarse o requerir un servicio externo.
6. Como reutilizar el mismo patron fuera del notebook.

## Ruta publica canonica

Todo notebook importa una sola fachada:

```python
import agentic_systems as toolkit
```

La ruta pedagogica de construccion es:

```python
toolkit.tool(...)
toolkit.skill(...)
toolkit.agent(...)
toolkit.system(...)
toolkit.graph(...)
toolkit.environment(...)
toolkit.eval(...)
```

Las clases publicas permanecen disponibles para typing, extension y control
avanzado, pero los notebooks deben preferir las factories anteriores cuando
construyen los conceptos centrales.

La agnosticidad es obligatoria: Provider, framework y estrategia se seleccionan
mediante rutas y registries publicos. Un valor fijo solo se admite como fallback
reproducible y debe quedar declarado; nunca como logica de dominio escondida.

## API antes que codigo local

Un notebook puede declarar datos, funciones de dominio, callbacks y fixtures
pequenos para hacer observable una conducta. No debe:

- reimplementar una capacidad que ya ofrece `toolkit`;
- importar modulos internos de `agentic_systems`;
- depender de codigo escondido en `examples/` o en otro tutorial;
- usar mocks o clases `Fake*` para afirmar que un Provider real se ejecuto;
- sustituir contratos, resultados, lineage, environments o evals por
  diccionarios fabricados cuando existe una API publica equivalente;
- reportar un skip de infraestructura como ejecucion exitosa.

Los inputs de demostracion deben estar nombrados y ser faciles de cambiar. Un
ejemplo determinista es valido cuando ensena la API; deja de serlo cuando toda
la conducta importante esta hardcodeada fuera de la libreria.

## Estructura esperada

Cada notebook contiene:

1. objetivo o historia de usuario;
2. parametros editables;
3. modelo mental y ownership;
4. construccion mediante `toolkit`;
5. ejecucion o skip explicito;
6. resultado humano primero y evidencia estructurada despues;
7. al menos un limite, fallo o riesgo;
8. inventario final `api_coverage`.

## Evidencia de release

El gate automatizado valida estructura, imports, compilacion y uso de la ruta
canonica. El gate manual ejecuta cada notebook desde un kernel limpio y registra
`pass`, `explicit skip` o `fail`. Las llamadas live a Providers solo se afirman
cuando existe evidencia de esa ejecucion.
