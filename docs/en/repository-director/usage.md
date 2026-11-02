# Use Repository Director

**English** | [日本語](../../repository-director/usage.md)

[Overview](README.md) · [Installation](installation.md) · [Validation](validation.md)

## Document existing code

```text
$repository-director
Inspect the code, tests and existing documents. Organize upstream specifications, AGENTS and README. Keep the implementation unchanged and discuss consequential unknowns.
```

Inspect the overall structure and requested scope, then trace functionality, permissions, core logic, data and tests.
Default to three docs: purpose.md for business goals/background and main features, architecture.md for file responsibilities,
entrypoints and major call/data flows, and development.md for execution/testing/change/operations procedures.
README introduces the repository and how to install/use it, linking to these docs. Reuse existing specifications, names and indexes.
Use annotated file trees and Mermaid diagrams tied to actual files/functions. Keep investigation scope, creation history and
work reports out of the body; retain necessary uncertainty next to the affected behavior. Distinguish observed implementation,
agreed requirements and proposals. Test files do not prove test execution.
A documentation-only request does not change source, dependency definitions, lockfiles or databases.

For a monorepo, name the package. Parent policies apply, and unrelated packages remain unchanged.
For delegated policy decisions, say so explicitly. Development defaults include their reasons and assumptions; business intent and user agreement remain unknown unless supported.

## New projects and development

Ask for goals, requirements, architecture and verification for new work. During implementation, read the relevant documents, make the requested changes and checks, and update affected documentation.
Use research when technical uncertainty matters, rather than for every change. Small changes do not regenerate the document set.

## Delegate work through a PR/MR

Ask in plain language: “Use a task branch, implement and test the change, commit, push and open a PR.
I will decide when to merge. Respect our existing team rules.”
The agent first discovers the existing policy, base branch and templates, then agrees the target,
operations and conditions in a short proposal. The suggested default is branch → implement/test →
commit → push → create/update PR/MR → human merge decision.

Record the agreement in the existing policy and link it from AGENTS. Git workflow setup alone does
not generate a full set of specification drafts. Reuse the scoped agreement and the existing task
branch/PR for continuation rather than requesting permission again or creating duplicates.

Keep unrelated changes out of commits. Explain the problem, resulting behavior, rationale and actual
checks in the PR, retaining uncertainty and compatibility impact where relevant. Incomplete required
verification does not mean ready for review; use a Draft only for a useful, agreed consultation or
handoff. If disconnected, finish the possible local work, prepare the description and report what
was not pushed or published. Inspect existing results before retrying uncertain operations.

Merge requires a separate explicit request and fresh checks of the target, diff, required tests and
reviews. The default does not include releases or branch-protection changes.

At start/resumption, inspect related branches/PRs, pending changes, dependencies and integration order.
Reuse continuing work; isolate independent tasks with a separate branch/worktree. Verify against the latest
base before merging and regenerate shared outputs after integrating their maintained sources.

```bash
repository-director work-status --project /absolute/path/app --base main --compare work/related
```

`--base` is required and names the actual integration target; `--compare` is optional and repeatable.
The JSON reports repository-wide local branches, upstreams, worktrees, pending paths and shared paths,
without returning file contents, accessing the network or changing Git state. Remote freshness and merge
conflicts remain unchecked. No shared paths does not prove behavioral compatibility; ancestry containment
does not recognize squash merges or authorize branch deletion. Failed reads/revisions are errors or warnings;
an unknown comparison without a unique merge base returns `null`, not an empty success.
External clean/process filters are disabled, with affected working-file state reported as candidates.
Submodule working files remain unchecked.

## Helpers

```bash
repository-director inspect --project /absolute/path/app
repository-director init --project /absolute/path/app --mode existing
repository-director init --project /absolute/path/app --mode existing --apply
repository-director check --project /absolute/path/app
repository-director check --project /absolute/path/app --base main
```

Init places the three drafts and README/AGENTS navigation; it does not create a separate index by default.
Existing indexes are reused. It does not use AI to investigate or finalize specifications. The Skill performs that substantive work.
Existing text/rules are preserved and repeated initialization does not duplicate sections.
Map custom documents with `--document requirements=specs/current.md`; use `--index docs/navigation.md` for a custom index.
Roles: purpose, policy, requirements, architecture, core, verification. `--approach delegate` selects delegated draft guidance; `--agent claude` connects CLAUDE to the shared AGENTS.
The role names remain compatible with existing mappings; several roles can share a document. Remove the hidden draft marker
only after completing that document. The CLI/checker distinguishes scaffolds from completed prose.

Plugin helpers use the portable entry on Windows too:

```text
intelliforge kit-run repository-director --agent claude -- inspect --project <target>
intelliforge kit-run repository-director --agent claude -- check --project <target>
```

Check returns 0 for no structural errors, 1 for structural errors, and 2 for input/execution errors.
Drafts and unreachable documents are review candidates. Meaning, specification conformance and actual test results require content review and evidence. CI use is optional.

## Changes and remote collaboration

Ask for commit/PR/MR drafts or reviews with clear purpose, behavior, checks and remaining work.
Inspect the actual prose against the request, diff and evidence. Keep small changes concise and distinguish required fixes from optional suggestions.
A draft/review request does not imply posting. Use connected tools or official gh/glab, honor existing authorization, avoid duplicates and re-read remote changes after writing.
