# Use Repository Director

**English** | [日本語](../../repository-director/usage.md)

[Overview](README.md) · [Installation](installation.md) · [Validation](validation.md)

## Document existing code

```text
$repository-director
Inspect the code, tests and existing documents. Organize upstream specifications, AGENTS and README. Keep the implementation unchanged and discuss consequential unknowns.
```

Inspect the overall structure and requested scope, then trace functionality, permissions, core logic, data and tests.
Reuse existing specifications and add missing purpose, policy and core-logic explanations. Distinguish observed implementation, agreed requirements and proposals.
Record contradictions and unimplemented requirements. Static-only investigation is supported; test files do not prove test execution.
A documentation-only request does not change source, dependency definitions, lockfiles or databases.

For a monorepo, name the package. Parent policies apply, and unrelated packages remain unchanged.
For delegated policy decisions, say so explicitly. Development defaults include their reasons and assumptions; business intent and user agreement remain unknown unless supported.

## New projects and development

Ask for goals, requirements, architecture and verification for new work. During implementation, read the relevant documents, make the requested changes and checks, and update affected documentation.
Use research when technical uncertainty matters, rather than for every change. Small changes do not regenerate the document set.

## Helpers

```bash
repository-director inspect --project /absolute/path/app
repository-director init --project /absolute/path/app --mode existing
repository-director init --project /absolute/path/app --mode existing --apply
repository-director check --project /absolute/path/app
repository-director check --project /absolute/path/app --base main
```

Init places navigation and explicitly marked drafts; it does not use AI to investigate or finalize specifications. The Skill performs that substantive work.
Existing text/rules are preserved and repeated initialization does not duplicate sections.
Map custom documents with `--document requirements=specs/current.md`; use `--index docs/navigation.md` for a custom index.
Roles: purpose, policy, requirements, architecture, core, verification. `--approach delegate` selects delegated draft guidance; `--agent claude` connects CLAUDE to the shared AGENTS.

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
