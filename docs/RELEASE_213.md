# Publicación de 2.1.3 · completada

2.1.3 está publicada en TestPyPI, PyPI y GitHub con los mismos archivos aprobados.
Commit del tag: `3cf15b4195b1b0dbef5b7b0e0dc444fdcb5791a6`.

- [CI de main: Python 3.10–3.14](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/39898703661).
- [Sello](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/39899126948).
- [TestPyPI](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/39899262120).
- [PyPI y GitHub](https://github.com/JacoboGGLeon/agentic_systems/actions/runs/39899686918).

Los pasos siguientes documentan el procedimiento utilizado. Las mejoras actuales
de tutorials, examples y README no autorizan sobrescribir esta versión. La
[validación didáctica posterior](LEARNING_VALIDATION_213.md) tiene su propio presupuesto.


El PR conserva el wheel de la campaña final, su sdist, Studio y la evidencia.
GitHub Actions ejecuta ese wheel sin modo editable en Python 3.10–3.14.
La campaña live no se repite durante CI ni durante el ensayo de publicación.
`live-quality.yml` comprueba la campaña guardada cuando se solicita; no tiene
schedule ni claves. Otra campaña de inferencia requiere autorización y una
asignación persistente propia; nunca se reinicia el ledger durante CI.

## Antes de autorizar publicación

1. Exigir `quality` verde: cinco jobs `offline`, más `release-dry-run`.
   Estos ejecutan tests, cobertura, notebooks, examples, Studio, empaquetado,
   integridad, secretos y metadatos. El ensayo adjunta
   `reviewed-213-publication-preview`; no crea tags ni sube archivos a índices.
2. Revisar el [informe de RunResult y Lineage Memory](RUNRESULTS_LINEAGE_213.md),
   el [inventario de notebooks](NOTEBOOK_INVENTORY_213.md) y las
   [notas preparadas](RELEASE_NOTES_213.md).
3. Mantener el PR abierto hasta autorizar su integración. Después, `main`
   debe tener su propio `quality` verde en el commit integrado.

La evidencia local anterior identifica el commit base de desarrollo; no afirma
que un commit futuro ya estuviera validado. El nuevo manifiesto enlaza los
mismos artefactos con el commit de ensamblado. Los cambios operativos desde
el snapshot se enumeran sin borrar el manifiesto original ni sus fallos.

## Sellar después de integrar

En Actions, ejecutar `release-candidate.yml` sobre `main`, indicando
`quality_run_id`: el run verde del commit exacto de `main`.
El job rechaza otra rama, otro commit y una matriz incompleta. Comprueba las
declaraciones de SDK, Studio y notebooks contra los bytes revisados; empaqueta
la evidencia y crea `certified-release-candidate` durante 90 días.

Guardar el ID de este nuevo run y el SHA-256 de `release-manifest.json`, mostrado
en el resumen del job. Este manifiesto es distinto del snapshot local histórico.
No requiere una prerelease pública ni un tag provisional.

## Publicación, cuando se autorice

Ejecutar `release.yml` sobre `main` con `candidate_run_id`, `manifest_sha256`,
`index=testpypi` y `confirm_publish=false` para verificar sin subir. Para subir,
se necesita una nueva autorización y `confirm_publish=true`.

Tras TestPyPI y sus smoke tests, usar el mismo run y el mismo SHA de manifiesto
para `index=pypi`. El job exige que TestPyPI tenga ambos archivos con los mismos
hashes. Versiones parciales, yanked o hashes diferentes bloquean la publicación;
ningún archivo se sustituye. Una repetición con hashes completos e idénticos
omite la subida y vuelve a comprobar instalación.

Los Trusted Publishers siguen usando owner `JacoboGGLeon`, repositorio
`agentic_systems`, workflow `release.yml` y entornos `testpypi` / `pypi`.
La configuración de cuentas no demuestra una publicación: conservar los URLs
de los runs cuando ocurra.

Solo después de publicar en PyPI y pasar sus smoke tests se habilita la
finalización de GitHub Release. `confirm_publish=false` no crea ni publica
releases o tags. El ZIP de Studio es una entrega separada; no se sube su wheel
a PyPI en este flujo.

Pendientes fuera del perfil: vLLM/Colab GPU, AWS IAM y ADA IAM. No hay extra
`[ada]`, ADA Studio ni wallet. Los runners no reciben claves de inferencia.
