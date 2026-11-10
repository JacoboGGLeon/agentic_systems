# Artifacts
Keep SDK wheel/sdist, Studio, notebooks and skill ZIP distinct. Pin the SDK
version and record SHA-256. Do not claim pip install materializes application
folders. Keep historical evidence immutable and do not attribute it to new bytes.

This 2.1.6 skill generates local applications. Publishing requires an explicit
release task with CI and artifact promotion gates. Do not overwrite published
versions, tags or files, or publish merely to finish a documentation update.

The next SDK release bundles the authoring skill in its wheel. `skill install` copies
it to a new directory; `skill export` creates a ZIP for manual import. These offline
commands never overwrite an existing path or register a personal ChatGPT skill.
