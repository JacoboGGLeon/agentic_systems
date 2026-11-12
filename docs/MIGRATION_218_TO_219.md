# Migrate from 2.1.8 to 2.1.9

This candidate aligns current teaching, example targets and the bundled authoring Skill around the core construction grammar. The SDK execution API is unchanged by this documentation update.

Install the 2.1.9 candidate wheel before running the updated notebooks; use registry commands after publication. Upgrade optional Studio/ADA packages together with the matching SDK when using them. Export the version-matched authoring Skill from the installed wheel. Skill install/export refuses existing destinations; select a fresh path instead of overwriting local work.

Agent(graph=...) remains a graph-based actuator; Agent(runtime=...) remains an actor. Runtime and Framework are independent. Explicit Agent contracts/policies remain advanced API options; they are not required for the introductory path. Expanded control-object acceptance is planned for 2.1.10.

Current notebook pins and metadata target 2.1.9. Old saved cell outputs were cleared where source pins changed. Recorded_Outputs.ipynb intentionally displays 2.1.8 records and reads immutable JSON evidence. Rerun active notebooks to establish candidate acceptance; do not rename baseline evidence as new results.

[Get started](../README.md) · [Current validation](VALIDATION_219.md) · [Historical 2.1.8 notes](RELEASE_NOTES_218.md).
