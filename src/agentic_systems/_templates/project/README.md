# Pedidos — Agentic Systems 2.1.3

Una sola API: `import agentic_systems as toolkit`. Este proyecto depende del
SDK 2.1.3 y no incluye otra gramática ni un paquete de compatibilidad.

En un entorno con el wheel 2.1.3 y sus dependencias instalado:

```text
python app.py --both
python test_offline.py
python execute_notebook.py
```

El sistema se declara una sola vez en `src/order_fulfillment/system.py`.
Tools y Skills aportan capacidades a los siete Agents. El flujo valida,
calcula precio e inventario en paralelo y decide aprobar, revisar o rechazar.
Environment entrega registros; Eval comprueba las respuestas exactas.

Los datos y expectativas son fixtures locales. El séptimo contrato verifica un
fallo técnico de inventario y la conservación del precio calculado. El rechazo
de negocio es una ejecución correcta; el fallo técnico devuelve `ok=False`.

`.env.example` describe la configuración sin credenciales. Solo se permite
python-runtime y AGENTIC_LIVE=0 en este ejemplo. El guard offline permanece
activo durante el proceso; Jupyter/asyncio requieren su transporte local.

La evidencia se produce al ejecutar; generar una plantilla no acredita que
haya pasado. El inventario es una fotografía fija por pedido y no se hacen
reservas, envíos ni notificaciones reales.
