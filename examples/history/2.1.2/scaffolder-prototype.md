# Scaffolder completo — revisión de API 2.1.3

2.1.3 identifica esta candidata de revisión de API. El paquete publicado 2.1.2
permanece intacto y se utiliza como baseline de compatibilidad. La gramática
mínima todavía vive en `unified_grammar`: no se presenta como disponible al hacer
`pip install agentic-systems==2.1.3`. No se ha publicado esa versión en esta tarea.

## Estructura de la librería

Este árbol ubica las responsabilidades de la revisión sobre el repositorio
existente. No es una reorganización destructiva ni una nueva colección de
constructores. Los directorios internos del SDK se conservan.

```text
agentic_systems/
├── pyproject.toml                   # distribución y extras existentes
├── src/agentic_systems/             # SDK publicado; compatibilidad 2.1.2
│   ├── factories.py                # factories públicas heredadas
│   ├── agents.py / system.py       # contratos existentes
│   ├── tools/ / skills/            # capacidades
│   ├── environments.py / evals.py  # episodios y evaluación
│   ├── integrations/               # frameworks
│   ├── providers/                  # proveedores
│   └── results.py / lineage.py     # resultados y trazabilidad
├── examples/
│   ├── README.md / catalog.json    # ejemplos y estado real de evidencia
│   └── unified_grammar/
│       ├── core.py                 # candidata de gramática mínima 2.1.3
│       ├── scaffold.py             # generador de proyectos independientes
│       ├── scaffold_template/      # entrada, configuración y empaquetado
│       ├── order_challenge/        # lógica compartida del challenge
│       ├── 00_walkthrough.ipynb    # seis ejemplos y challenge ejecutado
│       ├── tests/                  # contratos y regresiones offline
│       └── evidence/               # resultados medidos y hashes
├── tests/                          # regresiones del SDK
├── docs/                           # contrato, migración y alcance
└── .github/workflows/              # controles y publicación existentes
```

La futura incorporación al SDK necesita una decisión de promoción de API y
validación de los runtimes no cubiertos aquí. Este scaffolder no parchea los
exports públicos ni activa inferencia. Los pendientes de vLLM/Colab, IAM y ADA
siguen pendientes; la etiqueta 2.1.3 ya identifica la revisión de API solicitada.

## Proyecto que genera

```text
mi_proyecto/
├── app.py                          # entrada offline
├── pyproject.toml                  # dependencias y extras test/notebook
├── .env.example / .gitignore
├── README.md
├── manifest.json                   # objetivo 2.1.3, baseline 2.1.2, estado
├── SHA256SUMS.txt
├── src/
│   ├── order_challenge/
│   │   ├── __init__.py
│   │   ├── tools.py                # ocho operaciones deterministas
│   │   ├── skills.py               # siete paquetes de capacidades
│   │   ├── system.py               # única declaración del sistema
│   │   ├── settings.py             # configuración sin credenciales
│   │   ├── verification.py         # contratos y evidencia
│   │   └── fixtures/
│   │       ├── catalog.json
│   │       └── cases.json
│   └── unified_grammar/            # fachada experimental, no copia del SDK
│       ├── __init__.py
│       ├── core.py
│       └── offline.py
├── notebooks/01_order_challenge.ipynb
├── tests/test_contract.py
├── test_offline.py
├── execute_notebook.py
├── docs/SCAFFOLDER_213.md
└── evidence/                       # se completa al ejecutar, no al generar
```

## Generar y ejecutar

Desde el repositorio, con un destino nuevo:

```text
python examples/unified_grammar/scaffold.py /ruta/a/mi_proyecto
```

Desde el proyecto generado, en un entorno con las dependencias instaladas:

```text
python app.py --both
python test_offline.py
python execute_notebook.py
```

La generación es local, no instala paquetes y rechaza destinos existentes.
El proyecto funciona fuera del repositorio: el notebook, las pruebas y la entrada
importan el mismo constructor `order_challenge.system.build_system`.

La versión objetivo del proyecto de referencia es 2.1.3; su dependencia del SDK
2.1.2 es deliberada para medir compatibilidad. El manifiesto distingue ambas.
Los agentes del challenge son operadores Python y todos sus datos son fixtures.
