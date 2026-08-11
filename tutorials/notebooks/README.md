# Notebook Walkthrough Map

Los notebooks activos viven directamente en `tutorials/`. Este archivo es un
índice auxiliar y no define una segunda ruta de aprendizaje.

## Ruta Canónica

La lista completa y el orden de los 18 notebooks se mantienen en
[tutorials/README.md](../README.md). Todos usan:

```python
import agentic_systems as toolkit
```

## Gate De Mantenimiento

Para cada release:

1. la suite valida JSON, imports públicos, outputs limpios y compilación;
2. los 13 notebooks deterministas se ejecutan desde kernels limpios;
3. los 5 notebooks de Provider se validan estáticamente y exponen un preflight
   explícito;
4. no se atribuye ejecución a Strands u OpenAI Agents SDK;
5. un skip de infraestructura nunca cuenta como evidencia live.
