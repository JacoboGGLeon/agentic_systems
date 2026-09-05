# Publish once, verify every time

The release is an identity, not a fresh build on every retry. The wheel, source
archive, Studio, skill and validation bundles travel together under one reviewed
manifest. Repeating publication must not change their bytes or move their tag.

This runbook describes the automated publication path. A configured Trusted
Publisher is a prerequisite, not evidence that an OIDC publication has succeeded.
Record the actual Actions run URLs before claiming that either index was tested.

## What users receive

- PyPI: the `agentic-systems` wheel and source distribution, including the CLI.
- GitHub Release: matching Studio and skill ZIPs, enterprise and challenge
  bundles, certification summary, checksums and `release-manifest.json`.
- Studio remains a separate application. Installing the core package does not
  create a Studio notebook or application directory.

## One-time setup

Register a GitHub Trusted Publisher for `agentic-systems` on **each** index:

| Field | PyPI | TestPyPI |
| --- | --- | --- |
| Owner | `JacoboGGLeon` | `JacoboGGLeon` |
| Repository | `agentic_systems` | `agentic_systems` |
| Workflow filename | `release.yml` | `release.yml` |
| Environment | `pypi` | `testpypi` |

If the project does not exist on TestPyPI, register a pending publisher in the
account's Publishing page. These are independent accounts and registrations.
See the [official PyPI instructions](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

Both GitHub environments must restrict deployment to the `main` branch. The
workflow also rejects dispatch from other branches. Only the publishing job has
`id-token: write`; only the final GitHub-release job has `contents: write`.
There is no long-lived PyPI token, password input or `skip-existing` escape hatch.
The privileged workflow dependencies are pinned to reviewed commit SHAs.

## Build, certify and seal

1. Finish the source, documentation, tests and bundle changes. Use a new version
   whenever packaged material changes; never rebuild over a published version.
2. Pass `quality.yml` on the candidate commit. Build wheel and sdist once into a
   dedicated directory. Install that wheel non-editably outside the repository.
3. Run the required offline, semantic and target-environment checks on those
   exact bytes. Read the answers and lineage. Preserve provider, framework,
   authentication route, commit and wheel SHA256 in the evidence.
4. Assemble and audit the corresponding application bundles and certification
   summary. Missing external evidence is a blocker, not an implicit pass.
5. Run `python scripts/build_release_manifest.py --directory <candidate-directory>`.
   Review its artifact inventory and retain the printed manifest SHA256 outside
   the staging release.
6. Upload the complete candidate to a **public prerelease** under a staging tag,
   not the final `v<version>` tag. Dispatch `release-candidate.yml` on `main` with
   its numeric `staging_release_id` and the reviewed `manifest_sha256`.

The sealing workflow checks the successful quality run, commit, manifest hash,
every listed file hash and the ADA bundle verifier. Its successful Actions run
owns the `certified-release-candidate` artifact for 90 days. A mutable staging
asset cannot silently change the sealed candidate: hashes are checked again.

An offline quality artifact alone is **not** a semantically certified candidate.
The live certification summary records separate certified and assembly commits;
the sealing run must match the assembly commit in the manifest.

## TestPyPI, then PyPI

Dispatch `release.yml` on `main` with:

- `candidate_run_id`: the successful **release-candidate** run, not a quality run;
- `manifest_sha256`: the independently reviewed manifest digest;
- `index`: first `testpypi`, then `pypi`;
- `confirm_publish`: `false` for verification only, `true` to publish or resume.

Use the same candidate run and digest for both indices. After the first success,
repeat the dispatch on the same index. Record both run URLs. The repeated run
must reach `matching` and omit the upload action, while still verifying the
published files and clean installation.

| Observed index state | Action |
| --- | --- |
| Version absent (HTTP 404) | Permit the OIDC upload of wheel and sdist. |
| Complete filename, kind and SHA256 set matches | Skip upload; repeat post-publication checks. |
| Partial, unexpected, yanked or conflicting files | Stop without deleting or replacing anything. |
| Authentication, metadata or network failure | Stop; never interpret it as absence. |

Only classified transient network failures are retried, with bounded attempts.
PyPI's two-file upload is not transactional: if interrupted after one upload,
the partial state deliberately blocks automatic publication. Investigate it;
do not rename a conflicting build, delete a published version or bypass hashes.

Post-publication smokes download the exact wheel from the selected index, verify
its SHA256 and install it in clean Python 3.10 and 3.14 jobs. Dependencies resolve
from PyPI without an additional TestPyPI dependency index. Before publication,
wheel installation is also checked on Python 3.10 through 3.14.

## Close GitHub Release

Only a successful production publication and post-publication smoke unlock the
finalizer. It checks the remote tag and existing assets, creates or resumes a
draft, uploads only missing files, downloads all assets to verify their bytes,
and then marks the release final. It never uses `--clobber` or moves a tag.

A final release with exactly matching bytes is a no-op. A conflicting or
incomplete final release is left untouched and reported as an error. Keep the
staging release until final verification and evidence review are complete.

The closing report should include the version, commit, manifest digest, both
TestPyPI runs, both PyPI runs, final release URL, tested combinations and any
explicitly untested surfaces. A green unit test or HTTP health check alone is
not an end-to-end release certification.
