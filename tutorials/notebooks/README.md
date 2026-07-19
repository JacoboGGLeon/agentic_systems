# Notebook Walkthrough Map

Los notebooks activos viven directamente en `tutorials/`. Este archivo es solo
un indice auxiliar y no define una segunda ruta.

## Ruta Canonica

La lista completa y el orden de los 18 notebooks se mantienen en
`tutorials/README.md`. Todos usan:

```python
import agentic_systems as toolkit
```

## Gate 1.1

Antes de promover `1.1.0rc1`:

1. la suite valida JSON, imports publicos, outputs limpios y compilacion;
2. cada notebook se ejecuta manualmente desde un kernel limpio;
3. los Providers ausentes producen un skip explicito;
4. no se atribuye ejecucion a Strands u OpenAI Agents SDK.
