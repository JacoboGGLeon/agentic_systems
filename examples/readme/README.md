# Introductory README checks · Agentic Systems 2.1.9

The root README teaches a comparison capability, a model actor declaration, System composition, context/history/episodes and independent evaluation. Its Python declarations are visible and use the same sample throughout.

Run `python scripts/check_readme_examples.py` with the installed candidate and Bedrock extra. The script executes local blocks, checks stopping and Memory, rejects incorrect expectations and invalid windows, and simulates Bedrock transport to inspect the actor's two Tool choices. No model inference is performed. Results are written to `.tmp/readme-validation/validation.json` with the exact README hash and installed SDK version.

The complete real-data source is in `examples/time_series_discovery_219`. Its output viewer displays historical 2.1.8 evidence; that is separate from candidate acceptance. The older `incident_response.py` remains a previous teaching example, not the current README's executable source.
