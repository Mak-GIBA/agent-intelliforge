# Use the ECC entry Skills

**English** | [日本語](../../codex-ecc/usage.md)

[Overview](README.md) · [Installation](installation.md)

## First request

Open a new Codex session after installation. Automatic selection is enabled; name an entry explicitly when needed.

```text
$ecc-python Review this project's Python code and organize its types and exception handling.
$ecc-errors Design external API retries with recovery and duplicate-execution prevention.
$ecc-security Review the authentication changes, including secrets and authorization checks.
$ecc-library Select the relevant original procedures for this project's database migration and consider the migration steps.
```

## Entries and originals

| Entry | Original |
|---|---|
| `ecc-python` | `python-patterns` |
| `ecc-errors` | `error-handling` |
| `ecc-security` | `security-review` |
| `ecc-library` | Search API, testing, database, Docker, and other specialized Skills |

Search narrows candidates to at most 5, then reads the relevant 1–3 originals. Resolve relative references from the original Skill directory and load only needed assets. Existing React, Cloudflare, GitHub, and memory Skills take priority for their domains. Current user, developer, and project instructions override ECC guidance.

## Inspect from the terminal

Run at the repository root:

```bash
python3 tools/ecc-on-demand/ecc_on_demand.py search 'Python tests' --json
python3 tools/ecc-on-demand/ecc_on_demand.py search 'DB migration' --json
python3 tools/ecc-on-demand/ecc_on_demand.py resolve api-design --json
bash install_ecc.sh --doctor
```

Search uses names, descriptions, and some project structure. If results do not fit, use English technical terms or an original Skill name. `resolve` returns the body path, Skill directory, Plugin root, and version, rather than printing the whole body. Outside the repository, use the installed CLI; see [management](../ecc-on-demand.md).

## Storage and limits

The CLI and restoration state live in `ecc-on-demand/` beneath Codex's configuration directory. Entry Skills live in the user Skill directory. Originals remain in the Plugin cache, with paths resolved from the current catalog each time, including after updates.

Using an entry does not authorize automatic ECC re-enabling, installation, or updates. The bundled SessionStart injection of prior summaries, instincts, and learned Skills is disabled. Basic Memory and Codex conversation resumption are separate mechanisms. For errors, see [troubleshooting](installation.md#troubleshooting).
