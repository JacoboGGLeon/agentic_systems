# Publishing Agentic Systems 2.1.8

Publication uses the repository workflows and never overwrites a version, tag or asset.

1. Merge the release PR only after quality passes on Python 3.10–3.14.
2. Require quality to pass again for the exact main commit.
3. Dispatch release-candidate.yml with quality_run_id and acceptance_policy_sha256
   (the SHA-256 of release/policy-2.1.8.json).
4. The candidate downloads quality-built bytes, verifies the reviewed executable
   equivalence policy, and seals a manifest and separate SDK/Studio/skill/evidence assets.
5. Review the manifest hash and dispatch release.yml for testpypi, then pypi.
   Both dispatches use the same candidate_run_id and manifest_sha256, with confirm_publish=true.
6. Production requires the identical complete distributions on TestPyPI. Post-publish
   installation checks and the GitHub finalizer verify those same bytes and never move tags.

The reviewed policy pins the exact executable payload, including the additive evidence() API.
The user authorized closure of 2.1.8; no live inference is implied. acceptance.json must state that no live calls were made
against the stable wheel. This is not permission to waive executable differences.
Known limitations, including Bedrock/Qwen required nullable omission, remain documented.
See RELEASE_NOTES_218.md and release/policy-2.1.8.json.
