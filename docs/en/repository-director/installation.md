# Install, update and migrate Repository Director

**English** | [日本語](../../repository-director/installation.md)

[Overview](README.md) · [Usage](usage.md) · [Validation](validation.md)

## Installation

The standalone Linux/WSL2 script requires Bash and Python >=3.11. It embeds the Skill, helpers and tests and installs without downloads.
Codex is not installed. Authenticated gh/glab or an existing connector is needed only for the corresponding remote operations.

```bash
bash install_repository_director.sh --dry-run
bash install_repository_director.sh --apply
bash install_repository_director.sh --doctor
bash install_all.sh --only repository-director --apply
intelliforge inspect --only repository-director
intelliforge install --only repository-director --apply
intelliforge install --only repository-director --agent claude --apply
```

No arguments preview the plan and inspect ownership/conflicts. Doctor checks local installation and CLI availability, without authentication, network or model calls.
Native Windows uses the shared CLI's Plugin route. Claude support remains experimental. See [host support](../cross-platform.md).

## Locations and boundaries

Defaults: `~/.agents/skills/repository-director/`, `~/.local/bin/repository-director`, and `~/.local/share/repository-director/install.json`.
An owned routing block is added to Codex's global AGENTS, or a nonempty AGENTS.override.md. Unrelated rules are retained.
Override absolute locations with `RD_SKILLS_DIR`, `RD_BIN_DIR`, `RD_DATA_HOME` and `CODEX_HOME`; default data also follows XDG_DATA_HOME.
Use the same settings for updates, diagnosis and removal. Installation does not change project documents, sources, dependencies, remotes or hooks.
The Plugin route delegates registration to the selected host manager and uses the same maintained Skill/runtime.

## Legacy migration

The `speckit` and `github-pm` IDs, former scripts and Skill commands are retired, without compatibility aliases.

```bash
bash install_repository_director.sh --migrate-legacy
bash install_repository_director.sh --migrate-legacy --apply
intelliforge install --only repository-director --agent claude --migrate-legacy
intelliforge install --only repository-director --agent claude --migrate-legacy --apply
```

Migration verifies ownership records and hashes, backs up unedited owned resources outside Skill discovery, and retires legacy Skills/launchers/global guidance.
Plugin registrations are removed through the host manager and re-read. Old runtime history remains available.
On failure local resources are restored; any failed host-registration recovery is reported explicitly.
Edited, foreign, added or differently owned resources stop migration. Export them safely and manually reconcile the rules you want to retain.
For custom Upstream installs retain their original `SWB_SKILL_DIR`, `SWB_BIN_DIR` and XDG settings.
Project documents, .specify, reports, approvals, specify itself and its venv are retained, without automatic conversion.
The shared CLI preview describes the route; it does not prove authentication or full migration feasibility.

## Maintenance

```bash
bash install_repository_director.sh --update --dry-run
bash install_repository_director.sh --update --apply
bash install_repository_director.sh --uninstall
bash install_repository_director.sh --uninstall --apply
bash install_repository_director.sh --self-test
bash install_repository_director.sh --extract /absolute/path/empty-directory
```

Only unedited owned files are updated/removed. Project documents and backups remain. Extraction writes to an empty destination.
Self-test checks isolated functionality, not model writing quality or live service writes.

Disabled legacy Plugins are preserved; resolve their intended state through the host manager before migration.
