# Plan de implementación: álgebra computacional de sistemas inteligentes

Estado: RFC no aceptado; trabajo potencial posterior al checkpoint `1.1.3`
Horizonte: `1.2` a `2.0`  
Principio rector: semántica y leyes antes que azúcar sintáctica.

## 1. Punto de partida

La línea `1.1` ya cierra la gramática pública y observable:

```python
import agentic_systems as toolkit

toolkit.tool(...)
toolkit.skill(...)
toolkit.agent(...)
toolkit.system(...)
toolkit.graph(...)
toolkit.environment(...)
toolkit.eval(...)
```

También existen contratos estables para `RunResult`, sustitución de Providers,
composición de Tools y Skills, Graphs portables, Environments, Evals e
inspección estática. Esta base no debe reabrirse durante el trabajo algebraico.

La siguiente etapa no consiste en agregar más sustantivos. Consiste en poder
componer los sustantivos actuales mediante operadores con significado preciso,
observables, ejecutables sobre distintos Providers y verificables mediante
leyes.

## 2. Resultado buscado

Queremos expresar una computación inteligente como un valor inspeccionable:

```python
program = toolkit.sequence(
    researcher,
    toolkit.parallel(fact_checker, risk_checker),
    toolkit.fallback(writer, safe_writer),
)

result = toolkit.run(program, input=question, runtime=runtime)
```

El mismo `program` debe poder:

1. inspeccionarse sin ejecutar;
2. validarse contra capacidades y contratos;
3. ejecutarse con OpenAI, vLLM, Bedrock o un runtime local compatible;
4. producir evidencia normalizada sin inventarla;
5. compararse con otra expresión bajo una noción explícita de equivalencia;
6. optimizarse solamente cuando una ley demuestre que el cambio preserva la
   semántica declarada.

## 3. Decisiones que se congelan antes de programar

### 3.1 No crear otro universo de objetos

La representación intermedia, o IR, debe referenciar `Tool`, `Agent`, `Graph`,
`Environment` y `Eval`; no duplicarlos como nodos alternativos con otra
semántica.

### 3.2 Funciones explícitas antes que sobrecarga de operadores

La primera API será:

```python
toolkit.sequence(...)
toolkit.parallel(...)
toolkit.choice(...)
toolkit.fallback(...)
toolkit.repeat(...)
toolkit.run(...)
```

No se introducirán inicialmente operadores como `>>`, `|`, `&` o `*`. Ese
azúcar sólo podrá evaluarse después de estabilizar significado, errores,
precedencia y representación textual.

### 3.3 El álgebra describe composición, no un Provider

Ningún nodo de la IR puede importar SDKs de OpenAI, AWS, vLLM o frameworks. La
selección de Provider pertenece al runtime y el Provider concreto debe quedar
registrado en la evidencia de ejecución.

### 3.4 No prometer equivalencia de texto generado

La equivalencia inicial se definirá sobre contratos observables: forma de
entrada y salida, estado, Tool events requeridos, validación, errores,
terminación y efectos declarados. Igualdad de texto, costo, latencia o calidad
no se inferirá por cambiar de Provider.

### 3.5 `RunResult` continúa siendo el sobre estable

Una composición puede contener resultados intermedios, pero no debe mutarlos ni
fabricarlos. El resultado final debe conservar evidencia ordenada de ramas,
intentos, fallbacks y validaciones.

## 4. Modelo mínimo propuesto

### 4.1 Expresión

Definir internamente una familia cerrada e inmutable de expresiones:

```text
Expression
├── Primitive(reference)
├── Sequence(children)
├── Parallel(children, join)
├── Choice(selector, branches)
├── Fallback(primary, alternatives, policy)
└── Repeat(body, stop, max_iterations)
```

Cada expresión debe exponer, como mínimo:

- identidad estable o fingerprint estructural;
- hijos y orden declarado;
- contratos de entrada y salida;
- capacidades requeridas;
- efectos declarados;
- política de fallos;
- representación serializable e inspeccionable.

### 4.2 Intérprete

Un intérprete ejecuta una expresión usando las abstracciones actuales:

```text
Expression + input + Runtime + policy
    -> resolución y validación
    -> ejecución de primitivas existentes
    -> composición de evidencia
    -> RunResult
```

El intérprete portable será la referencia semántica. Adaptadores nativos de
Graph o frameworks podrán optimizar después, siempre comparados contra esta
referencia.

### 4.3 Efectos

Los efectos no deben inferirse del nombre de una Tool. Comenzarán con una
taxonomía pequeña y extensible:

```text
pure        no modifica estado externo declarado
read        consulta estado externo
write       modifica estado externo
network     requiere red
model       invoca un modelo
human       requiere intervención humana
```

La ausencia de una declaración significa `unknown`, nunca `pure`.

## 5. Checkpoints de implementación

### Checkpoint 1.2.0 — Especificación de la IR

Objetivo: cerrar el significado antes de ejecutar nada.

Entregables:

- ADR de representación, propiedad y extensibilidad de `Expression`;
- tabla de tipos para entrada, salida, estado y error;
- definición normativa de los cinco combinadores;
- esquema serializable versionado;
- ejemplos y contraejemplos por operador;
- decisión explícita sobre cómo una primitiva referencia Tool, Agent o Graph.

Gate:

- la especificación puede representar diez composiciones reales del repo sin
  Provider ni framework;
- ninguna clase pública nueva duplica una abstracción de `1.1`;
- el documento responde qué ocurre con entrada, salida, evidencia y fallo en
  cada operador.

### Checkpoint 1.2.1 — IR inmutable e inspección

Objetivo: construir expresiones sin ejecutarlas.

Entregables:

- tipos internos de IR;
- `toolkit.sequence`, `parallel`, `choice`, `fallback` y `repeat`;
- coerción explícita de primitivas soportadas;
- `expression.to_dict()` e inspección humana mediante `toolkit.show`;
- fingerprints estructurales deterministas;
- validación de ciclos, ramas vacías, nombres repetidos y límites inválidos.

Gate:

- tests unitarios y de snapshot estructural;
- serialización JSON estable;
- importar `agentic_systems` no carga dependencias opcionales;
- construir e inspeccionar una expresión no ejecuta Tools, modelos ni red.

### Checkpoint 1.2.2 — Intérprete portable secuencial

Objetivo: ejecutar `Primitive` y `Sequence` con semántica de referencia.

Entregables:

- `toolkit.run(expression, input=..., runtime=..., policy=...)`;
- propagación explícita de valores entre pasos;
- reglas para short-circuit y errores;
- composición no destructiva de `RunResult`;
- sync y async con semántica equivalente;
- trazas con identidad de expresión y paso.

Gate:

- las primitivas siguen usando sus APIs públicas existentes;
- ningún intérprete llama directamente un SDK de Provider;
- fallos intermedios conservan evidencia;
- pruebas de sustitución con Providers falsos normalizados;
- cobertura total del código nuevo y suite completa verde.

### Checkpoint 1.2.3 — Parallel, Choice, Fallback y Repeat

Objetivo: completar el núcleo operacional sin esconder decisiones.

Entregables:

- política de unión de resultados para `parallel`;
- selector observable para `choice`;
- predicado y lista de intentos para `fallback`;
- condición de parada y límite obligatorio para `repeat`;
- cancelación, timeout y límites de concurrencia integrados con scheduler;
- metadatos de ruta solicitada y ruta realmente ejecutada.

Gate:

- `parallel` conserva orden declarativo aunque termine fuera de orden;
- `fallback` nunca presenta degradación como ruta primaria exitosa;
- `repeat` no puede crearse sin un límite finito verificable;
- elección, intentos y cancelaciones quedan en evidencia estructurada;
- tests deterministas de carreras, cancelación y error parcial.

### Checkpoint 1.3.0 — Leyes algebraicas y equivalencia

Objetivo: pasar de composición ejecutable a álgebra verificable.

Entregables:

- definición de equivalencia estructural;
- definición de equivalencia observacional por contrato;
- catálogo de leyes con precondiciones;
- property-based tests;
- `toolkit.equivalent(left, right, contract=..., cases=...)` como verificador,
  no como afirmación mágica;
- contraejemplos documentados para leyes que no siempre aplican.

Leyes candidatas iniciales:

```text
sequence(identity, a) ≈ a
sequence(a, identity) ≈ a
sequence(sequence(a, b), c) ≈ sequence(a, sequence(b, c))
parallel(a, b) ≈ parallel(b, a)        sólo con join conmutativo y efectos seguros
fallback(a, a) ≈ a                     sólo si repetir a no agrega efectos
choice(always_left, a, b) ≈ a
```

Gate:

- ninguna ley ignora efectos, fallos o límites del scheduler;
- cada ley incluye precondiciones ejecutables;
- property tests encuentran deliberadamente implementaciones mutantes
  incorrectas;
- equivalencia entre Providers se reporta por contrato y casos, no por nombre.

### Checkpoint 1.4.0 — Sistema de efectos y capacidades

Objetivo: impedir transformaciones inseguras y mejorar preflight.

Entregables:

- declaraciones de efectos y capacidades en primitivas;
- análisis estático agregado de expresiones;
- incompatibilidades antes de ejecutar;
- políticas para red, escritura, modelo, intervención humana y costo;
- reporte de efectos en `system.inspect()` y expresión inspeccionada.

Gate:

- una rama con efectos desconocidos bloquea optimizaciones que exijan pureza;
- Providers reciben requisitos explícitos, no inferidos por hardcode;
- errores de capacidad incluyen entidad, requisito y remediación;
- secretos nunca aparecen en inspección, fingerprint ni serialización.

### Checkpoint 1.5.0 — Intérpretes y optimización portable

Objetivo: permitir múltiples mecanismos de ejecución sin cambiar significado.

Entregables:

- protocolo interno de intérprete;
- intérprete portable como oracle de referencia;
- compilación opcional a Graph nativo;
- adaptadores de framework sólo donde exista ejecución real;
- pases de optimización gobernados por leyes;
- reporte antes/después y razón de cada reescritura.

Gate:

- portable y nativo pasan el mismo corpus contractual;
- toda optimización puede desactivarse;
- cada reescritura cita ley y precondiciones satisfechas;
- fallback a portable es explícito y observable;
- no se declara soporte nativo cuando sólo existe metadata de estilo.

### Checkpoint 2.0.0 — Álgebra pública estable

Objetivo: promover únicamente las piezas demostradas en `1.2`–`1.5`.

Entregables:

- API pública final y baseline de compatibilidad;
- especificación formal versionada;
- migración desde composición `1.1` sin ruptura innecesaria;
- tutorial que construye, inspecciona, ejecuta, compara y optimiza un programa;
- matriz live OpenAI, vLLM y Bedrock;
- benchmark de costo de interpretación y volumen de evidencia;
- release candidate y validación manual de notebooks.

Gate de salida:

- un mismo programa corre por al menos tres Providers configurados sin cambiar
  su definición;
- las diferencias reales se reflejan en capacidades y evidencia;
- las leyes promovidas tienen pruebas de propiedades y contraejemplos;
- la API no requiere que el usuario conozca la IR interna;
- `Run All` cuenta una historia completa sin resultados fabricados.

## 6. Estrategia de pruebas transversal

Cada checkpoint debe agregar cuatro capas de evidencia:

1. **Unitarias:** construcción, validación, serialización y errores.
2. **Propiedades:** leyes, invariantes y generación de expresiones pequeñas.
3. **Conformidad:** mismo contrato normalizado en python-runtime, OpenAI, vLLM y
   Bedrock mediante dobles controlados.
4. **Live:** notebooks o smoke tests opt-in para Providers configurados, sin
   convertir ausencia de credenciales en resultados ficticios.

Los Providers live prueban integración, no determinismo semántico. Los tests de
leyes deben ser reproducibles y no depender de modelos externos.

## 7. Tutoriales previstos

No se crearán notebooks por cada clase interna. La secuencia pedagógica debe
seguir problemas de usuario:

1. componer dos operaciones con `sequence`;
2. ejecutar validaciones independientes con `parallel`;
3. elegir una ruta por estado con `choice`;
4. degradar explícitamente con `fallback`;
5. iterar con límite y evidencia usando `repeat`;
6. cambiar OpenAI por vLLM o Bedrock sin reescribir el programa;
7. verificar una ley y observar cuándo no aplica;
8. inspeccionar efectos antes de ejecutar;
9. comparar intérprete portable y backend nativo.

Cada celda de cómputo debe preferir la API pública. Helpers locales sólo se
aceptan para datos propios del dominio, nunca para reconstruir capacidades que
ya pertenecen a `toolkit`.

## 8. Riesgos y defensas

| Riesgo | Defensa |
|---|---|
| Crear una DSL bonita pero semánticamente vacía | Funciones explícitas, especificación y contraejemplos primero |
| Confundir Graph con la nueva álgebra | IR declarativa separada; Graph es un posible intérprete/backend |
| Ocultar diferencias entre Providers | Perfiles de capacidad y evidencia del Provider real |
| Declarar leyes falsas para sistemas con efectos | Precondiciones de efectos y property tests |
| Inflar `RunResult` hasta volverlo inmanejable | Evidencia jerárquica, referencias y proyecciones sin mutación |
| Hardcodear rutas OpenAI/Bedrock/vLLM | Registro de Provider y protocolos de capacidad existentes |
| Convertir optimización en magia | Reescrituras inspeccionables, desactivables y justificadas por ley |
| Romper la claridad tutorial | Un problema de usuario por notebook y `Run All` como criterio de producto |

## 9. Orden de trabajo para mañana

### Bloque A — 60 a 90 minutos: cerrar significado

1. Crear ADR de la IR.
2. Escribir las firmas propuestas de los cinco combinadores.
3. Resolver por escrito tres preguntas:
   - ¿qué tipos pueden ser primitivas?;
   - ¿cómo fluye el valor entre hijos?;
   - ¿qué evidencia mínima debe producir cada operador?
4. Elegir diez composiciones actuales como corpus de aceptación.

Checkpoint: no comenzar código hasta que las tres respuestas no tengan
contraejemplo y regla de error.

### Bloque B — 2 a 3 horas: primer corte vertical

1. Implementar `Primitive` y `Sequence` internos.
2. Exponer `toolkit.sequence`.
3. Agregar inspección y serialización.
4. Implementar el intérprete portable sobre dos Tools y un Agent.
5. Producir un `RunResult` con evidencia ordenada.

Checkpoint: demo local `sequence(tool_a, agent_b)` construible, inspeccionable y
ejecutable sin importar SDKs opcionales.

### Bloque C — 60 a 90 minutos: endurecer

1. Agregar tests unitarios y de propiedades para identidad y asociatividad de
   `sequence` bajo precondiciones válidas.
2. Ejecutar suite y cobertura completas.
3. Confirmar compatibilidad del API baseline de `1.1`.
4. Revisar que ningún resultado sea fabricado o mutado.

Checkpoint: suite verde, cobertura conservada y cero cambios incompatibles en
`PUBLIC_API` salvo `sequence` y, si ya está listo, `run`.

### Bloque D — 45 a 60 minutos: tutorial y decisión

1. Crear una demostración mínima centrada en un problema real.
2. Ejecutarla con python-runtime.
3. Ejecutar preflight de OpenAI, vLLM y Bedrock.
4. Registrar decisiones, deuda y la siguiente rebanada.

Checkpoint: decidir continuar, ajustar semántica o descartar el diseño antes de
implementar los otros cuatro operadores.

## 10. Criterio para detenerse

Se detiene la implementación y se vuelve al diseño si ocurre cualquiera de
estos casos:

- la IR necesita duplicar `Agent`, `Graph` o `RunResult`;
- una regla depende del nombre concreto de un Provider;
- no puede explicarse qué evidencia se conserva tras un error;
- asociatividad o identidad sólo funcionan ignorando efectos relevantes;
- el tutorial necesita acceder a módulos internos para contar la historia;
- la API obliga a cambiar la definición del programa para cambiar de Provider.

## 11. Primera decisión arquitectónica pendiente

La pregunta que desbloquea todo el trabajo es:

> ¿Cuándo consideramos equivalentes dos sistemas inteligentes?

Propuesta inicial:

> Dos expresiones son observacionalmente equivalentes respecto de un contrato y
> un conjunto de casos cuando, bajo las mismas capacidades declaradas, ambas
> satisfacen el contrato, conservan las invariantes de estado y evidencia
> exigidas, y exhiben efectos y categorías de fallo compatibles. No se requiere
> igualdad de texto, latencia, costo ni mecanismo interno salvo que el contrato
> lo declare.

Esta definición debe aprobarse o corregirse antes de promover optimizaciones o
afirmar leyes públicas.
