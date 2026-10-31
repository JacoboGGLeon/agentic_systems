# CLI y scaffolder · 2.1.4.dev8

El wheel del SDK instala `agentic-systems`.

| Comando | Input → proceso → output |
|---|---|
| `agentic-systems version` | Sin datos → identidad instalada → versión |
| `agentic-systems api` | Sin datos → API pública instalada → JSON de nombres |
| `agentic-systems doctor` | Dependencias locales → inspección de módulos → JSON; no prueba servicios ni claves |
| `agentic-systems new mi_proyecto` | Destino nuevo → copiar plantilla vigente → aplicación, tests, example y notebook |

```console
agentic-systems new mi_proyecto
cd mi_proyecto
python app.py
python examples/quote.py
```

La aplicación demuestra Tools, Skills, Graph, Agents, System, Context, Memory,
Environment, Eval y RunResult. Las declaraciones están en src y se explican en
el notebook. `tests/test_refund.py` contiene el control positivo y el rechazo de
un campo obligatorio ausente. Se necesita pytest para ejecutar esos tests.
Un destino existente se rechaza sin sobrescribirlo.

El cierre local prueba el proyecto fuera del checkout, incluyendo notebook y
actores native, OpenAI Agents y Strands con Python determinista. Generar archivos
no acredita acceso a un LM; la plantilla empieza offline.

El paquete independiente ADA instala `agentic-systems-ada doctor`. Su diagnóstico
lee indicadores de configuración sin resolver credenciales ni consultar AWS.
[Contrato AWS/ADA](ADA_214.md) · [Instalación](../INSTALL.md) ·
[Evidencia](../revisions/2.1.4/grammar-dev8/closure/scaffolder-build07/scaffolder.json).
