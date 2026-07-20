# SteerCo Demo Runbook - Agentic Systems 1.1

Fecha de presentacion: 2026-07-20.
Duracion recomendada: 12 minutos + preguntas.

## Mensaje central

> Agentic Systems no es otro wrapper de prompts. Es una gramatica computacional
para construir, ejecutar, observar y evaluar sistemas inteligentes con contratos
y evidencia consistentes entre runtimes.

## Lo que pedimos al SteerCo

1. Reconocer `1.1.0` como baseline estable.
2. Validar la direccion: coherencia y evidencia antes que acumulacion de features.
3. Autorizar que la siguiente fase empiece por descripcion y analisis de los
   componentes existentes, sin ampliar aun la gramatica publica.

## Flujo de 12 minutos

### 0:00-1:30 - El problema

Los prototipos agenticos suelen ocultar cuatro decisiones: que Provider corrio,
que Tools estuvieron disponibles, que evidencia produjo la ejecucion y como se
verifica el resultado. Agentic Systems convierte esas decisiones en API y datos
inspeccionables.

### 1:30-3:00 - La gramatica publica

Mostrar solamente:

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

Explicar que la construccion vive bajo `toolkit.system(...)`; la clase `AgenticSystem` queda como superficie avanzada. El factory no selecciona Provider: recibe la ruta declarada por `toolkit.runtime(...)`.

### 3:00-6:00 - Demo principal

Abrir `tutorials/08_system_api.ipynb` y ejecutar o mostrar:

1. construccion de `toolkit.system`;
2. registro de Tools y Skill;
3. creacion del Agent;
4. `system.inspect()` antes de ejecutar;
5. `toolkit.human_result(...)` despues de ejecutar.

Frase de transicion:

`inspect()` explica lo que podria pasar; `RunResult` conserva lo que realmente
paso.

### 6:00-8:30 - Verificacion, no solo demo

Abrir `tutorials/10_environment_eval_api.ipynb` y mostrar:

- episodios y transiciones;
- reward y estado;
- `toolkit.eval().run(...)`;
- casos, pass rate, reproducibilidad y evidencia.

Evitar recorrer todas las celdas. Mostrar el input editable, la API y el reporte
final.

### 8:30-10:00 - Portabilidad con limites honestos

Mostrar la matriz de Providers en `docs/MANUAL_NOTEBOOK_MATRIX_1_1.md`.

Mensaje:

- `python-runtime`: ejecucion local verificada;
- OpenAI, Bedrock y vLLM: contratos y conformance verificados;
- ejecuciones live externas no se inventan ni se infieren;
- OpenAI Agents-style y Strands son identidades declarativas, no SDK adapters.

### 10:00-12:00 - Evidencia de cierre

```text
Version: 1.1.0
Tests: 392 passed
Coverage: 100.00% / 6,193 statements
Notebooks: 18/18 ejecutados
Wheel + sdist: twine check passed
Wheel: instalado e importado en venv nuevo
```

Cerrar con:

`La propuesta no es que confien en la demo; es que puedan inspeccionar y repetir
la evidencia.`

## Demo de respaldo

Si Jupyter, red o credenciales fallan:

1. no intentar una llamada live;
2. usar `python-runtime`;
3. mostrar `docs/RELEASE_1_1.md`;
4. mostrar la matriz 18/18;
5. ejecutar `python -m pytest -q tests/release/test_release_candidate_contract.py`.

El fallback no reduce el claim porque la presentacion no depende de Providers
externos.

## Preguntas probables

### Es production-ready?

La base de composicion, contratos, evidencia y packaging esta cerrada. La release
no afirma que todos los Providers externos hayan sido certificados live en todos
los ambientes productivos.

### Por que no usar directamente LangGraph, OpenAI Agents o Strands?

Pueden usarse como mecanismos de ejecucion u orquestacion. Agentic Systems define
el contrato portable, la evidencia y las fronteras que esos backends deben
preservar.

### Que significa 100% de cobertura?

Significa que las ramas del paquete estan ejercitadas por pruebas; no significa
que los modelos sean correctos ni que una cuenta externa este disponible.

### Por que `AgenticSystem` no es lowercase?

Porque `agentic_systems.system` ya es un submodulo soportado. Ocultarlo romperia
compatibilidad. Se privilegio estabilidad sobre simetria cosmetica.

### Cual es el siguiente paso?

Una descripcion uniforme y verificable de Tool, Skill, Agent y System, reutilizando
inspection, contracts y Provider profiles antes de introducir algebra o IR publica.

## No decir

- que todos los Providers fueron ejecutados live;
- que Strands u OpenAI Agents SDK ya tienen adapter;
- que 100% coverage prueba calidad semantica de respuestas;
- que Graph es la representacion universal;
- que 1.1 ya contiene el algebra de 2.0.
