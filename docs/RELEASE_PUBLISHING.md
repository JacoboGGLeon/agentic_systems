# Publishing Agentic Systems 2.1.9

Publication uses the repository workflows and never overwrites a version, tag or asset.

1. Merge the release PR only after quality passes on Python 3.10–3.14.
2. Require quality to pass again for the exact main commit.
3. Dispatch release-candidate.yml with quality_run_id and acceptance_policy_sha256
   (the SHA-256 of release/policy-2.1.9.json).
4. The candidate downloads quality-built bytes, verifies the reviewed executable
   equivalence policy, and seals a manifest and separate SDK/Studio/skill/evidence assets.
5. Review the manifest hash and dispatch release.yml for testpypi, then pypi.
   Both dispatches use the same candidate_run_id and manifest_sha256, with confirm_publish=true.
6. Production requires the identical complete distributions on TestPyPI. Post-publish
   installation checks and the GitHub finalizer verify those same bytes and never move tags.

The version-specific policy and final artifact manifest for 2.1.9 are still pending preparation and review. They must reflect the actual executable and bundled-resource differences; never copy old payload hashes or claim old live acceptance applies to the new wheel. Candidate sealing also requires a successful mutation gate on the exact main commit.

The SDK, optional applications, learning bundle and authoring Skill ZIP are distinct assets. Keep their versions coherent. The README's 2.1.9 Skill download URL becomes available only after finalization. See [candidate notes](RELEASE_NOTES_219.md) and [validation scope](VALIDATION_219.md).
