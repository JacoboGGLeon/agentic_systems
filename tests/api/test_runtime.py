from __future__ import annotations

from ._load_legacy import export_legacy_tests

export_legacy_tests(
    globals(),
    'agentic_systems_api',
    'agentic_systems_coverage_complete',
    'bedrock_converse_contract',
    'bedrock_phase7_coverage',
    'checkpoint_00_decoupling',
    'checkpoint_01_cleanup_preflight',
    'checkpoint_04e_policy_and_bedrock_names',
    'checkpoint_08_python_direct_engine',
    'checkpoint_08b_bedrock_runtime_engine',
    'checkpoint_08c_canonical_runtime_paths',
    'cli',
    'notebook_aws_utils',
    'package_surgery_imports',
    'phase7_residual_coverage',
    'providers_phase1_coverage',
    'tutorial_import_path',
)
