# API observada del wheel · 2.1.4.dev8

15 conceptos propios, cinco reexportaciones originales de LangGraph y __version__. Métodos nativos de Pydantic/LangGraph pertenecen a esas bibliotecas y no son constructores nuevos. Graph requiere un owner para obtener RunResult; compile del owner valida el subconjunto integrado de LangGraph.

## Agent

```python
Agent(name: 'str', graph: 'Any' = None, skills: 'tuple' = (), runtime: 'Any' = None, framework: 'Any' = None, instructions: 'str' = '', policy: 'dict | BaseModel | None' = None, *, context: 'Context | None' = None, memory: 'Memory | None' = None, contract: 'dict | None' = None) -> None
```

- arun(self, input=None, *, timeout_s=None)
- compile(self)
- inspect(self)
- run(self, input=None, *, timeout_s=None)

## Context

```python
Context(data, *, sources=())
```

- to_dict(self)
- Properties: data, episodes, fingerprint, lineage, sources

## Environment

```python
Environment(name: 'str', graph: 'Any', records: 'Any', max_steps: 'int | None' = None, state: 'Any' = None, observe: 'Callable | None' = None, update: 'Callable | None' = None, stop: 'Callable | None' = None, *, context: 'Context | None' = None, memory: 'Memory | None' = None) -> None
```

- arun(self, *, timeout_s=None)
- compile(self)
- inspect(self)
- run(self, *, timeout_s=None)

## Eval

```python
Eval(name: 'str', unit: 'Any', cases: 'tuple', checks: 'tuple' = (), judge: 'Agent | None' = None, rubric: 'dict | None' = None) -> None
```

- arun(self, *, timeout_s=None)
- compile(self)
- inspect(self)
- run(self, *, timeout_s=None)

## Memory

```python
Memory(*, capacity=20)
```

- read(self)
- remember(self, result)

## RunResult

```python
RunResult(text: 'str' = '', final: 'dict' = <factory>, data: 'dict' = <factory>, ok: 'bool' = True, messages: 'tuple' = (), tool_events: 'tuple' = (), raw_responses: 'tuple' = (), usage: 'dict' = <factory>, engine: 'str' = 'python-runtime', model: 'str' = '', mode: 'str' = 'default', trace_schema_version: 'str' = 'agentic_systems.trace.v1', validation: 'dict | None' = None, errors: 'tuple' = (), meta: 'dict' = <factory>, execution_id: 'str' = <factory>, parent_execution_id: 'str | None' = None, children: 'tuple' = (), status: 'str' = '', interrupts: 'tuple' = (), continuation: 'dict | None' = None) -> None
```

- check_invariants(self)
- human_results(self, *, max_steps=8, max_chars=4000)
- lineage(self, *, name='run', question=None, goal='', tags=None, metadata=None, max_tool_rows=3)
- to_dict(self)
- trace(self, mode='compact', *, max_steps=20)
- walk(self)

## System

```python
System(name: 'str', graph: 'Any' = None, *, context: 'Context | None' = None, memory: 'Memory | None' = None, contract: 'dict | None' = None) -> None
```

- arun(self, input=None, *, timeout_s=None)
- compile(self)
- inspect(self)
- run(self, input=None, *, timeout_s=None)

## framework

```python
framework(name, *, agent_kwargs=None, run_kwargs=None)
```

- boundaries(self)
- describe_sdk_objects(self, value)
- inspect(self)

## load_skill

```python
load_skill(path)
```

- inspect(self)

## model_artifact

```python
model_artifact(model, *, base_model=None, adapter_path=None, tokenizer=None, revision=None, quantization=None, metadata=None)
```

- inspect(self)

## model_server

```python
model_server(artifact, *, profile='fast', served_model_name=None, host='127.0.0.1', port=8000, tool_call_parser='hermes', reasoning_parser=None, enable_auto_tool_choice=True, api_key='vllm', startup_timeout_s=600.0, log_path='vllm-server.log', binary='vllm', extra_args=(), gpu_memory_utilization=None, max_model_len=None, max_num_seqs=None)
```

- health(self)
- inspect(self)
- start(self)
- stop(self)
- Properties: command, endpoint

## pause

```python
pause(value)
```


## runtime

```python
runtime(*, provider, model=None, region=None, endpoint=None, api_key=None, timeout_s=60.0, max_retries=0, max_tool_calls=5, max_turns=6, max_tokens=None, backoff_s=0.0, max_concurrency=1, session=None)
```

- inspect(self)
- model_post_init(self: 'BaseModel', context: 'Any', /) -> 'None'
- provider_options(self)

## skill

```python
skill(*, name, description='', tools=(), instructions='', version='0.1.0', metadata=None)
```

- inspect(self)

## tool

```python
tool(function=None, /, *, name=None, description=None, input_schema=None, output_schema=None, metadata=None)
```

- arun(self, input=None)
- inspect(self)
- run(self, input=None)

## Objetos devueltos y protocolo de nodo

No se construyen directamente. run/arun devuelven RunResult; __call__(state) en Tools/Agents/Systems es el protocolo de nodo que entrega una actualización al Graph.

### compile()

- aresume(self, paused, value)
- arun(self, input=None, *, timeout_s=None)
- inspect(self)
- resume(self, paused, value)
- run(self, input=None, *, timeout_s=None)

### RunResult.lineage()

- explain(self)
- render(self)
- to_dict(self)
- to_prompt_context(self, *, max_chars=1600)

### RunResult.check_invariants()

- to_dict(self)
