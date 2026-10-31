# Qwen con vLLM en este equipo · preparación pendiente

Equipo observado: Windows, NVIDIA RTX 3070 Laptop GPU, 8192 MiB. No hay WSL ni
vLLM instalados y `http://127.0.0.1:8000/v1/models` no respondió. Esta receta no
se ejecutó: **vLLM GPU no está validado**.

vLLM no soporta Windows nativo en su instalación oficial; propone Linux o WSL.
Microsoft documenta GPU en WSL y NVIDIA indica usar el driver Windows para
WSL, sin instalar dentro de WSL un driver de pantalla Linux.

- [Instalación oficial vLLM GPU](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/)
- [GPU en WSL](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gpu-compute)
- [NVIDIA CUDA en WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)

## Preparar Linux una vez

En PowerShell como administrador, si decides preparar el equipo:

```powershell
wsl --install -d Ubuntu-24.04
```

Completar la instalación, crear el usuario Linux y reiniciar si Windows lo
pide. Después, dentro de Ubuntu:

```bash
nvidia-smi
sudo apt update
sudo apt install python3-venv
python3 -m venv ~/venvs/vllm-qwen
source ~/venvs/vllm-qwen/bin/activate
python -m pip install --upgrade pip
python -m pip install vllm
python -m pip freeze > ~/vllm-qwen-requirements.txt
```

El freeze fija lo realmente instalado para esa prueba, no versiones adivinadas
antes de disponer del entorno. Confirmar que el driver satisface los requisitos
del wheel vLLM instalado; la resolución de dependencias y `nvidia-smi` por sí
solos todavía no certifican inferencia.

## Arrancar un Qwen pequeño

Primero descargar de memoria el Qwen de Ollama si sigue activo, desde PowerShell:

```powershell
ollama stop qwen3:4b-instruct-2507-q4_K_M
```

Elegimos **Qwen/Qwen3-0.6B**, repositorio oficial Qwen y ejemplo explícito de los
[modelos soportados de vLLM](https://docs.vllm.ai/en/stable/models/supported_models/).
Es un primer smoke test para los 8 GiB disponibles; no una declaración de que
un modelo de 0.6B tendrá la calidad del Qwen32B de Bedrock.

En Ubuntu, con el venv activado:

```bash
vllm serve Qwen/Qwen3-0.6B \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 2048 --max-num-seqs 1 \
  --gpu-memory-utilization 0.75 --enforce-eager
```

El primer arranque descarga pesos. Conservar la revisión resuelta de
Hugging Face, versiones, comando, logs y uso GPU. Estos parámetros reducen
contexto/concurrencia y evitan captura CUDA graph; la memoria libre real puede
exigir ajustes explícitos. No usar el servidor junto con otro modelo GPU en
este equipo de 8 GiB.

Comprobar sin generar texto:

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/v1/models
```

Esto comprueba disponibilidad, no compatibilidad de Agentic Systems. Probar
también el acceso desde Windows; el reenvío localhost de WSL debe funcionar
antes de congelar el endpoint de una campaña.

## Conectar Agentic Systems después

Con el **wheel exacto** de `revisions/2.1.4/candidate/` instalado en el cliente
Python, la declaración será:

```python
reasoner = toolkit.runtime(
    provider="vllm-runtime", model="Qwen/Qwen3-0.6B",
    endpoint="http://127.0.0.1:8000/v1", api_key="vllm",
    max_tokens=512, max_retries=0,
)
```

La expresión no ejecuta inferencia. La siguiente campaña deberá congelar pesos,
endpoint y SHA-256 del wheel, activar el contador persistente antes de llamar a
`run`, y comprobar respuestas/contratos/linaje y GPU. La campaña vigente y su saldo están en LEARNING_VALIDATION_214.md. No iniciar inferencia sin un contador activo.
Un modelo descargado, un GET satisfactorio o un proceso de servidor activo no
se contarán como celda aprobada.
