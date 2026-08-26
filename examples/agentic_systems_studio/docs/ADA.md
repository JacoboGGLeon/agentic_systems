# Run in ADA or restricted JupyterLab

1. Create a clean virtual environment or kernel.
2. Configure pip to use the approved Artifactory (`PIP_INDEX_URL`; credentials are
   platform configuration and never belong in this bundle).
3. Install the certified `agentic_systems-2.1.0-py3-none-any.whl` and the local
   Studio package with the `ui,notebook` extras.
4. At the ADA bundle root, copy `.env.example` to `.env`. This is the only runtime
   configuration file; select one provider/framework and keep credentials in the
   managed runtime or approved secret mechanism.
5. Run `00_conversational_system.ipynb` for the direct system contract.
6. Run `01_launch_studio.ipynb` for Streamlit through the JupyterLab proxy.

For Bedrock IAM, leave `AWS_BEARER_TOKEN_BEDROCK` empty. boto3 automatically uses
the ADA/SageMaker execution-role credential chain. Studio and its notebooks read
that choice from `.env` and never mutate the authentication route. For vLLM, point `VLLM_BASE_URL`
at the approved local or managed endpoint; Studio does not start a GPU server.

If a dependency conflicts with the base Jupyter image, do not mutate the shared
kernel. Recreate the isolated environment using versions mirrored in Artifactory.
