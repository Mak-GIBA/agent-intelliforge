# Agent Intelliforge documentation

**English** | [日本語](../README.md)

[Repository overview](../../README.md) · [Bulk installation](installation.md) · [Development](development.md)

[Shared CLI, Windows, and Claude Code](cross-platform.md) · [Distribution development](cross-platform-development.md) · [Additional-path validation (Japanese)](../cross-platform-validation.md)

Choose a kit by purpose, then read its overview, installation guide, and usage guide. For Codex on Linux / WSL2, start with [bulk installation](installation.md). For native Windows or Claude Code, start with the [shared CLI](cross-platform.md). If already installed, go directly to the usage examples.

| Purpose | Overview | Installation, updates, removal | Usage |
|---|---|---|---|
| Retain reusable knowledge | [Basic Memory Workgraph](basic-memory-workgraph/README.md) | [Install](basic-memory-workgraph/installation.md) | [Usage and settings](basic-memory-workgraph/usage.md) |
| Design, implement, and verify interfaces | [Codex UX Stack](codex-ux-stack/README.md) | [Install](codex-ux-stack/installation.md) | [Usage](codex-ux-stack/usage.md) |
| Repository policies and specifications from new or existing code | [Repository Director](repository-director/README.md) | [Installation](repository-director/installation.md) | [Usage](repository-director/usage.md) |
| Compare and evaluate core approaches | [Design Research](design-research/README.md) | [Install](design-research/installation.md) | [Usage](design-research/usage.md) |
| Read ECC procedures when needed | [Codex ECC](codex-ecc/README.md) | [Install, update, restore](codex-ecc/installation.md) | [Usage](codex-ecc/usage.md) |
| Read and edit Office files | [Office Workbench](codex-office/README.md) | [Install](codex-office/installation.md) | [Usage](codex-office/usage.md) |
| Improve Japanese writing | [kotonoha](kotonoha/README.md) | [Install](kotonoha/installation.md) | [Usage](kotonoha/usage.md) |
| Open a terminal workspace by directory | [Herdr](herdr/README.md) | [Install and configure Bash](herdr/installation.md) | [Usage](herdr/usage.md) |

## Combine kits

Use UX Stack to organize objects, actions, and states, then kotonoha to polish Japanese labels and explanations. Keep short labels short and required information visible.

### Design Research and Repository Director

Repository Director organizes purpose, requirements, architecture and verification for new or existing code.
Use Design Research when technical uncertainty warrants comparisons or experiments, then link the findings back to the design.
Research is not mandatory for every development task.

- [Repository Director usage](repository-director/usage.md)
- [Research usage](design-research/usage.md)
- [Validation](repository-director/validation.md)

## Workgraph details

- [Knowledge graph and examples](basic-memory-workgraph/knowledge-graph.md)
- [Sharing, importing, and training JSONL](basic-memory-workgraph/sharing.md)
- [Policy, layout, and mechanisms](basic-memory-workgraph/reference.md)
- [Troubleshooting and integrity checks](basic-memory-workgraph/troubleshooting.md)
- [Adoption evidence design and evaluation (Japanese)](../basic-memory-workgraph/evidence-design.md)

## ECC management CLI

[Read ECC on demand](ecc-on-demand.md) explains search, source resolution, updates, restoration, and disabled startup behavior.

## Reading command examples

Run `bash`, `python3`, and PowerShell blocks in a terminal. Unless stated otherwise, use the repository root. Enter `text` request examples in Codex. SpecKit project operations, Skill requests, and Herdr commands run in the target project.

A **Plugin** is a distribution unit; a **Skill** is a workflow Codex reads. **MCP** connects external tools to the host. A **CLI** runs terminal commands, and a **hook** responds to conversation or other events.

Guides describe this repository's scripts. External names and features may change; guides therefore include sources and ways to inspect the installed state.

## Develop and maintain guides

See [development](development.md) for checks, maintenance policy, and [new-installer templates (Japanese)](../_templates/installer/README.md). English and Japanese pages link to each other. Evaluation datasets, historical execution reports, and upstream originals remain unchanged; links identify Japanese-only material.
