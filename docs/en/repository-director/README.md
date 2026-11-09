# Repository Director

**English** | [日本語](../../repository-director/README.md)

[Install and migrate](installation.md) · [Usage](usage.md) · [Validation](validation.md) · [Docs](../README.md)

Document repository goals and implementation for developers, and develop against those documents.
Use it for new projects or to document existing code and add AGENTS/README guidance without changing the application.
It also handles GitHub Issues/PRs/Projects, GitLab Issues/MRs, and clear commit messages.
Agree the scope and conditions for work branches, verification, PR/MR creation and a separate reviewer's merge.
An existing PR-only agreement stays PR-only. See the [workflow example](usage.md#delegate-work-through-review-and-merge).

This custom kit replaces GitHub Project Director and SpecKit Upstream. The old scripts, kit IDs and Skill entrypoints are retired without aliases.
Official SpecKit, custom metadata, approval ledgers and research tools are not required. Existing documents and history can be retained.

README is the repository entrypoint: overview, prerequisites, installation, usage, commands, document links and license.
Keep business goals/background in docs/purpose.md, file responsibilities/entrypoints/call and data flows in docs/architecture.md,
and development/testing/change/operations procedures in docs/development.md. These are the three default documents.
AGENTS contains agent rules and references. Reuse existing names, indexes and specifications instead of duplicating them.
Use generated illustrations to introduce purpose, concepts and the overview; retain annotated trees and Mermaid for exact files/functions,
real screenshots for UI instructions and data-derived plots for measurements. Reuse suitable images and check figures against the source.
Preserve business context and
design rationale, while keeping investigation scope, document-creation history and work reports out of the document body.

```text
$repository-director
Document this existing code and organize AGENTS and README. Do not modify the implementation. Ask about consequential unknown requirements.
```

Dialogue is the default. Request delegated decisions to have development policies chosen with reasons and assumptions.
Business goals, user agreement and unexecuted test results are never invented. Installation does not initialize projects.
