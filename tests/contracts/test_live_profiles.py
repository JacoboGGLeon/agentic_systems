from __future__ import annotations

from agentic_systems.registry import FRAMEWORK_NAMES, MATRIX_CONTRACTS, PROVIDER_NAMES
from scripts.run_live_matrix import _load_profile


def test_live_profiles_are_registry_subsets_and_cover_release_matrix() -> None:
    pairs: set[tuple[str, str]] = set()
    for profile in ("cloud", "ollama", "python", "vllm"):
        providers, frameworks = _load_profile(profile)
        assert set(providers) <= set(PROVIDER_NAMES)
        assert set(frameworks) <= set(FRAMEWORK_NAMES)
        pairs.update(
            (provider, framework) for provider in providers for framework in frameworks
        )

    assert pairs == {(item.provider, item.framework) for item in MATRIX_CONTRACTS}
