# Toda la API, desde el usuario

Abre [01_api_user_guide.ipynb](01_api_user_guide.ipynb). Es autónomo y todas sus
celdas ejecutables son offline. Incluye los seis flujos y una aprobación de
pedidos con Tools, Skills, Agents, System, Environment y Eval.

```python
from examples.api_walkthrough.example import run

report = run()
report
```

La declaración de pedidos se comparte con la validación online; la configuración
del proveedor es explícita. El notebook no llama a proveedores externos.
[Inventario exhaustivo](../../docs/NOTEBOOK_INVENTORY_213.md).
