# Crítica de experiencia de usuario · revisión 2.1.4

> Crítica de la instantánea anterior a la limpieza didáctica dev5. La revisión
> posterior conserva runtime/scheduler como pilares, expone las construcciones
> antes ocultas y corrige la proyección de salidas Strands. Sus resultados y
> pendientes actuales están en [Estado](STATUS_214.md) y el
> [informe dev6](../revisions/2.1.4/grammar-dev6/REPORT.md).

Fecha: 2026-10-26. Revisión del código y material de aprendizaje local, sin
inferencia. Es una evaluación técnica de usabilidad; no sustituye una prueba
con desarrolladores nuevos ni certifica un release.

En la fecha de esta crítica, la fuente declaraba 2.1.4.dev5. La evidencia de artefacto revisada
corresponde a [dev4](../revisions/2.1.4/pydantic-dev4/REPORT.md). Los contratos
dev5 están en desarrollo; sus pruebas parciales no equivalen a aceptar un
wheel nuevo ni a ejecutar otra matriz online. Esta crítica identifica
pendientes; no afirma haberlos corregido.

## Veredicto

Agentic Systems tiene una propuesta valiosa y capacidades reales, pero todavía
no ofrece una experiencia uniformemente sencilla. A un desarrollador que
necesita coordinar operaciones, distintos SDK de agentes y evidencia de
ejecución puede resultarle atractiva. Para quien quiere su primer agente,
la cantidad de conceptos y decisiones iniciales puede desanimar.

| Pregunta | Evaluación actual |
| --- | --- |
| ¿Es óptima? | No puede afirmarse; hay fricciones concretas y falta observar usuarios nuevos. |
| ¿Dan ganas de usarla? | Sí para flujos compuestos que necesitan contratos y explicaciones; el beneficio es menos evidente en una operación pequeña. |
| ¿Es minimalista? | La superficie raíz está contenida, pero el modelo mental todavía es grande. |
| ¿Es sencilla? | Algunas operaciones son claras; construcción, configuración y depuración exigen demasiadas distinciones al principio. |
| ¿Es poderosa? | Sí: composición, decisiones, paralelismo, actores distintos, episodios y evaluación comparten resultados. |
| ¿Es robusta? | Hay evidencia offline importante y límites explícitos; la robustez operativa y la cobertura real de proveedores siguen siendo parciales. |

## El valor que conservaría

El valor principal es componer trabajo determinista y razonamiento de distintos
SDK sin reconstruir contratos, resultados y evidencia para cada integración.
LangGraph expresa el flujo; Agentic Systems aporta unidades con identidad,
Context, Memory, límites, evaluación y un RunResult común.

Esto importa cuando un pedido pasa por normalización, inventario, política,
revisión y decisión: interesa saber qué ocurrió, con qué información, dónde
falló y qué resultado puede consumir la siguiente unidad. Ahí la librería
ofrece más que una llamada a un modelo.

Conservaría la construcción explícita del grafo, las funciones Python para
decisiones, compile sin inferencia, run/arun, la validación de datos, el
resultado común y las vistas humanas acotadas. También conservaría la
separación entre Context, State, Memory y linaje: sus responsabilidades son
distintas aunque su enseñanza necesite mejorar.

## Fricciones observadas

### El primer ejemplo tarda en demostrar el beneficio

El [README](../README.md) comienza con un modelo, una Tool, un grafo, un nodo,
dos aristas y un Agent para multiplicar por dos. Es correcto y transparente,
pero el trabajo de preparación domina la operación. El usuario puede preguntar
por qué necesita una librería de sistemas agénticos para eso.

No resolvería esto añadiendo otro constructor abreviado. Mantendría el ejemplo
mecánico muy corto como explicación del flujo y mostraría inmediatamente un
problema pequeño que justifique la biblioteca: una decisión de negocio con
Context, una entrada inválida y un resultado explicable. El beneficio debe
aparecer antes de enseñar toda la referencia.

### Una sola importación no significa una sola carga conceptual

La raíz exporta 17 constructores/funciones core, seis objetos de LangGraph y
la versión. El número parece pequeño, pero no mide cuántas decisiones debe
tomar alguien para construir correctamente. También debe entender estados,
actualizaciones parciales, aristas, barreras, reducers, contratos, límites y
opciones de SDK.

Exponer LangGraph directamente evita mantener un lenguaje de grafos paralelo;
es una buena decisión técnica. A la vez, obliga a aprender parte de LangGraph.
La promesa precisa es una gramática común de composición sobre LangGraph,
no construir cualquier sistema sin conocer sus reglas.

### Agent tiene dos modos con reglas distintas

En la fuente, Agent exige graph o runtime. Si utiliza graph, rechaza
framework, instructions y policy. Si utiliza python-runtime, exige exactamente
una Tool declarada mediante Skills. Son restricciones explícitas, pero el
mismo nombre reúne dos experiencias que el usuario debe distinguir.

Un operador Python de un paso resulta especialmente incómodo si necesita
envolver una función en Tool, luego Skill y luego Agent para probar un SDK.
Para una función aislada enseñaría Tool.run. Enseñaría Agent cuando exista una
unidad de trabajo que merezca nombre, contexto o evidencia, y explicaría sus
dos modos con un ejemplo contiguo. No introduciría otra clase ni un alias.

### Las fronteras de configuración todavía cuestan

runtime selecciona ejecución y concentra controles del scheduler; framework
selecciona el actor y sus opciones particulares; policy gobierna su conducta;
contract declara requisitos; Limits acota la ejecución compuesta.

La división tiene fundamento, pero el usuario necesita una respuesta inmediata
a preguntas como: «¿Dónde pongo el timeout?», «¿Qué límite gana?» o «¿Un
timeout detiene realmente el trabajo?». Hay timeout de runtime y timeout
global; una espera agotada no garantiza que un trabajador haya terminado.

Pydantic mejora validación, errores y esquemas. No elimina estas decisiones.
La documentación debe mostrar propiedad, alcance, precedencia y efecto real
de cada control en una tabla y en pruebas negativas visibles. El primer
tutorial no necesita exhibir todas sus opciones.

### Context, State, Memory y linaje necesitan una explicación práctica

La distinción útil es:

| Elemento | Pregunta que responde | Ejemplo |
| --- | --- | --- |
| Context | ¿Con qué información de referencia opero? | Moneda y umbral de revisión con su fuente. |
| State | ¿Qué valores necesita el flujo ahora? | Pedido normalizado y decisión calculada. |
| Memory | ¿Qué episodios previos seleccionados puedo consultar? | Resultados acotados de ejecuciones anteriores. |
| Linaje | ¿Qué se ejecutó y qué evidencia dejó? | Tool utilizada, resultado, error e identidad de ejecución. |

No son cuatro almacenes intercambiables. Pero si cada uno vuelve a incluir el
pedido, la respuesta y la traza completos, el usuario verá duplicación.
Hay que enseñar referencias y resúmenes, y comprobar límites de volumen en
episodios largos. Que Memory esté acotada por número de entradas no demuestra
por sí solo un techo global de memoria, bytes o tokens de una aplicación.

El linaje acredita lo observado; no demuestra por sí mismo que una decisión
sea verdadera, causalmente correcta o semánticamente válida. Un snapshot de
Context tampoco es un mecanismo de autorización o una defensa completa
frente a contenido adversarial.

### Las salidas conservan demasiado vocabulario interno a la vista

RunResult es una buena unificación. Sin embargo, sus campos data, final, text,
messages, tool_events, raw_responses, meta y children, y sus vistas trace,
lineage y human_results, pueden competir por la atención del principiante.

La ruta inicial debería ser siempre result.status, result.ok, result.data y
result.human_results(). Después vendrían errors e invariantes, y finalmente
la evidencia detallada. Hay que explicar que una ejecución pausada puede tener
ok verdadero sin haber terminado: para decidir si hay respuesta final importa
status. No eliminaría evidencia necesaria para hacer más corto el objeto;
organizaría su presentación por propósito.

### Parte del aprendizaje todavía es una caja negra

La [auditoría estática de 26 notebooks](../revisions/2.1.4/contracts-dev5/visibility-before.json)
detecta nueve con imports de aplicaciones auxiliares. Cinco no contienen
llamadas toolkit visibles según ese análisis: contratos/jueces, pedidos,
interoperabilidad, Studio y Context/Memory. El análisis cuenta llamadas, no
todos los usos posibles de la API; no es una prueba completa de calidad.

Importar recursos o infraestructura de transporte puede ser apropiado. El
problema demostrativo concreto es importar demonstrate, build o verify y
ocultar allí la composición que la lección promete enseñar. Esto contradice
la exigencia de ejemplos explícitos del usuario y sigue pendiente en esta
instantánea.

Cada lección debe mostrar los elementos relevantes, su ejecución y sus
aserciones. Las funciones locales son útiles cuando su cuerpo se puede leer
en el propio ejemplo. No hace falta repetir todos los conceptos en todas las
lecciones. Tampoco contar varios wrappers del mismo experimento como nuevas
demostraciones independientes.

### La narrativa no identifica aún una única revisión vigente

La fuente declara dev5, README y API declaran dev4, y RELEASE_214 todavía dice
que la candidata con evidencia es dev3. Los artefactos anteriores deben
conservar identidad; el problema es no indicar desde una página de estado qué
está en desarrollo, qué artefacto fue probado y qué sigue pendiente.

Además, algunos documentos históricos enlazan guías distintas dentro del
mismo encabezado. Aunque estén marcados como históricos, la navegación puede
devolver al lector a una API anterior. Esto reduce confianza más rápido que
una firma larga: el desarrollador deja de saber qué puede copiar.

### Las capacidades avanzadas no son equivalentes entre rutas

LangGraph orquesta y los SDK implementan actores. Compartir RunResult no hace
idénticos los handoffs, sesiones, MCP/A2A, semántica de herramientas o métricas
de cada SDK. Las extensiones mediante agent_kwargs y run_kwargs preservan
capacidades particulares, pero requieren conocer el SDK correspondiente.

La promesa debe ser composición y evidencia comunes con capacidades
particulares explícitas. No equivalencia universal. Ollama nativo todavía
requiere que el perfil de entorno coincida con la conexión declarada; esa
dependencia oculta debe resolverse antes de prometer configuración inequívoca.

### Environment y Memory evocan más de lo que hoy ofrecen

Environment tiene episodios, estado, observación, actualización y parada.
No ofrece actualmente una API pública completa de reinforcement learning con
reset/step/reward/spaces. Memory conserva episodios locales acotados; no es
persistencia durable ni memoria semántica con recuperación vectorial.

Los nombres pueden conservarse si sus límites se explican al presentarlos.
Pausa y reanudación locales tampoco equivalen a recuperar un proceso tras
reiniciarlo. Un usuario de producción necesita saberlo antes de diseñar la
aplicación, no al final de una página de validación.

## Qué cambiaría antes de ampliar la gramática

1. Fijar una página de estado que distinga fuente en desarrollo, artefacto
   probado, capacidades ejecutadas y release publicado. Derivar de allí los
   enlaces y avisos de entrada.
2. Hacer autosuficientes las demostraciones: datos, declaraciones, ejecución,
   salida esperada y un fallo comprensible. En el primer recorrido, evitar
   dependencias de Studio para enseñar el SDK.
3. Enseñar una ruta progresiva: Tool, Agent, System, Environment y Eval.
   Incorporar Context cuando cambie una decisión y Memory cuando exista una
   segunda ejecución. Mostrar runtime/framework solo al conectar un actor.
4. Documentar las fronteras de configuración con una única tabla de
   propiedad y precedencia, y ejemplos mínimos de errores antes de efectos.
5. Usar una presentación breve por defecto y detalle bajo demanda. Validar
   que el linaje grande conserva lo necesario sin inundar al usuario.
6. Cerrar las inconsistencias concretas de integración y repetir la aceptación
   sobre el nuevo artefacto. No sustituir un caso fallido por otro más fácil.
7. Probar usabilidad con desarrolladores que no hayan diseñado la librería.
   Pedirles que construyan un flujo pequeño, lo modifiquen y diagnostiquen un
   fallo sin ayuda. Registrar tiempo, errores, conceptos que confunden y
   enlaces consultados; las pruebas actuales no miden eso.

No añadiría ahora otra palabra pública como harness, otra forma de construir
agentes ni un DSL. Primero hay que estabilizar la gramática disponible y
demostrar que se entiende. El desarrollo interno puede seguir siendo rico;
la primera experiencia debe exigir pocas decisiones.

## Recomendación y alcance de robustez

La recomendaría hoy para experimentar de forma controlada con composición,
contratos y evidencia, explicando que esta revisión sigue en desarrollo.
No la presentaría todavía como una base universal de producción ni como una
API óptima para cualquier usuario.

Dev4 conserva evidencia de 239 pruebas offline, 26 notebooks offline,
53 entrypoints offline y cuatro probes reales acotados. Las celdas live
omitidas no quedan validadas por ejecutar un notebook offline. En dev5 hay
resultados parciales de 208 regresiones y 32 pruebas de contratos; no son una
aceptación final de distribución. Ninguna de estas cifras sustituye una
evaluación de usabilidad, persistencia, operación prolongada o toda la matriz
proveedor/SDK.

Persisten el caso obligatorio Bedrock/Qwen con un nulo omitido, la adaptación
de workflows y la aceptación de artefactos nuevos. vLLM está aplazado por
decisión del usuario y debe permanecer fuera del alcance validado; no tiene
que bloquear un release cuyo perfil lo excluya explícitamente.

La descripción que mejor expresa su utilidad es: **coordina código y agentes
de distintos SDK, con contratos y evidencia de ejecución compartidos**. La
biblioteca será más atractiva cuando ese beneficio se perciba en el primer
ejemplo y se mantenga al depurar una ejecución compleja.
