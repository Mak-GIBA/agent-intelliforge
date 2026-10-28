#!/usr/bin/env bash
# ECC native install + five on-demand entrypoints + selected independent MCPs.
# Requires this repository. Existing MCP settings are preserved.
# Default: offline preview. --apply installs/configures; --update --apply updates.
# --mcps recommended|research|browser|cloudflare|none or comma-separated names.
# recommended: Firecrawl (keyless search/scrape/parse) + Chrome DevTools.
# crawl/map require Firecrawl authentication; existing MCP settings are preserved.
# This selection is not a proven general accuracy gain.
# Assessment: docs/codex-ecc/mcp-workflow-evaluation.md (preview includes reasons).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER="$SCRIPT_DIR/tools/ecc-on-demand/install_ecc.py"
[[ -f "$INSTALLER" ]] || {
  printf '%s\n' 'ERROR: tools/ecc-on-demand/ を含むリポジトリ一式が必要です。' >&2; exit 2;
}
command -v "${PYTHON_BIN:-python3}" >/dev/null || {
  printf '%s\n' 'ERROR: Set PYTHON_BIN to an available Python 3.11+ executable.' >&2; exit 2;
}
export PYTHONDONTWRITEBYTECODE=1
exec "${PYTHON_BIN:-python3}" -B "$SCRIPT_DIR/tools/ecc-on-demand/bootstrap.py" "$@"
