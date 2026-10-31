# runtime y scheduler · 2.1.4.dev8

`runtime(...)` es la única entrada pública de configuración de ejecución.
Conserva proveedor, modelo, conexión y los controles del scheduler que eran
pilares de 2.1.1/2.1.2. El scheduler interno conserva tiempos, reintentos,
backoff y executor; no requiere importar otro constructor.

| Declaración | Alcance | Efecto |
| --- | --- | --- |
| StateGraph | Dependencias de negocio | Secuencia, ramas, barreras y decisiones |
| runtime(provider, model, region, endpoint, api_key) | Actor | Identidad/conexión explícita; sin fallback |
| runtime(timeout_s, max_retries, backoff_s, max_concurrency) | Scheduler del actor | Espera, intentos y capacidad del executor |
| runtime(max_turns, max_tool_calls, max_tokens) | Actor/generación | Controles locales; no son dinero |
| Agent(policy, contract) | Actor/negocio | Conducta y requisitos verificables |
| run(timeout_s=60) | Raíz completa | Plazo compartido; hijos heredan el restante |
| Environment(max_steps, stop) | Episodios | Techo de records y parada de negocio |
| Contador persistente de campaña | Transportes reales | USD/solicitudes, incluidos fallos, reintentos y trabajadores tardíos |

No existe Limits ni limits= ni max_actions. nodes_observed solo mide
activaciones, no decide aceptación. Añadir envoltorios no agota una cuota.
La configuración Pydantic rechaza números inválidos, booleanos y cadenas en
controles estrictos. max_tool_calls=0 prohíbe Tools; max_turns debe ser positivo.

El timeout efectivo del scheduler respeta el mínimo entre su plazo local y
el restante de la raíz. No inicia otro reintento tras agotar la raíz y el
backoff no reinicia el plazo. Los intentos, errores y consumo se conservan.
El tiempo de espera humana en pausa no consume tiempo activo de la raíz.
Un nuevo run es otra ejecución; una reanudación conserva el mismo presupuesto
de tiempo. Un hijo no recibe timeout_s nuevo para resetearlo.

Los timeouts son cooperativos. Un hilo iniciado puede terminar tarde; no se
promete cancelación forzosa, rollback ni efectos exactly-once. Mantener
idempotencia y contador live hasta que terminen los trabajadores.

```python
execution = toolkit.runtime(provider="python-runtime", timeout_s=30,
    max_retries=0, max_turns=2, max_tool_calls=1)
# agent = toolkit.Agent(..., runtime=execution, skills=...)
result = system.run(input_data, timeout_s=60)
```

Para leer dominio, Tools y nodos usan `*, context: toolkit.Context`.
Runtime de LangGraph permanece interno; no es una segunda API pública.
[Lección](../tutorials/api/03_execution_controls.ipynb) ·
[Programa](../examples/execution_controls/example.py) · [API](API_214.md).
