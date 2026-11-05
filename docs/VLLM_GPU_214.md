# Qwen with vLLM: preparation, not GPU acceptance

Historical inspected machine: Windows, NVIDIA RTX 3070 Laptop GPU, 8192 MiB. WSL/vLLM were absent and the local models endpoint did not respond. This recipe was not executed: **GPU vLLM is not validated**. Recheck current vendor requirements before preparing another machine.

Use Linux or a supported WSL setup. Follow [vLLM GPU installation](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/), [Microsoft GPU compute in WSL](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gpu-compute) and [NVIDIA CUDA in WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html). Use the Windows driver as documented; do not install a Linux display driver inside WSL.

## Prepare Linux

If you choose to prepare the machine, use an administrator PowerShell:

```powershell
wsl --install -d Ubuntu-24.04
```

Finish installation, create a Linux user and restart if requested. In Ubuntu:

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

The requirements freeze records actual installed versions, not guessed versions. Check driver compatibility with the installed vLLM wheel. Dependency resolution and nvidia-smi do not certify inference.

## Start a small Qwen model

Unload the existing Ollama model first if it is still active:

```powershell
ollama stop qwen3:4b-instruct-2507-q4_K_M
```

Qwen/Qwen3-0.6B is a small initial smoke-test candidate, not a claim of parity with Bedrock Qwen32B. Check [supported models](https://docs.vllm.ai/en/stable/models/supported_models/) for the selected vLLM version. In the activated Ubuntu environment:

```bash
vllm serve Qwen/Qwen3-0.6B \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 2048 --max-num-seqs 1 \
  --gpu-memory-utilization 0.75 --enforce-eager
```

First startup downloads weights. Record resolved model revision, versions, command, logs and GPU usage. These parameters reduce context/concurrency and avoid CUDA graph capture; actual free memory may require explicit changes. Do not run another GPU model concurrently on this 8 GiB setup.

Check availability without generating text:

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/v1/models
```

Successful GET requests establish availability, not toolkit compatibility. Check Windows-to-WSL localhost forwarding before freezing the campaign endpoint.

## Connect Agentic Systems afterward

Install the exact candidate wheel in the Python client:

```python
reasoner = toolkit.runtime(
    provider="vllm-runtime", model="Qwen/Qwen3-0.6B",
    endpoint="http://127.0.0.1:8000/v1", api_key="vllm",
    max_tokens=512, max_retries=0,
)
```

This declaration executes no inference. Before run, freeze weights, endpoint and wheel SHA256 and activate the authorized persistent campaign counter. Verify responses, contracts, lineage and GPU execution. A download, successful GET or running process does not count as an accepted inference cell.
