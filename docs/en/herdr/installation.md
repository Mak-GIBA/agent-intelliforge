# Install Herdr and configure Bash

**English** | [日本語](../../herdr/installation.md)

[Overview](README.md) · [Usage](usage.md)

## Requirements and installation

Requires Bash on Linux / macOS and Python 3.8 or later. First-time downloads also need curl, the official installer's dependencies, and network access. This installer does not use sudo or pip.

```bash
bash install_herdr.sh --dry-run
bash install_herdr.sh
source ~/.bashrc
herdr --version
```

Existing Herdr is reused. Otherwise, the installer downloads `https://herdr.dev/install.sh`, executes it in a temporary directory, and checks the version and required CLI before placing files. Setup does not start a server.

| Item | Destination or change |
|---|---|
| New Herdr binary | `~/.local/bin/herdr` |
| Wrapper | `~/.local/bin/herdr-open` |
| Bash configuration | Managed `herdr-open: cwd workspace` block in `~/.bashrc` |

The managed block adds PATH configuration and a `herdr` function. Managed files are backed up before modification. A symlinked dotfile keeps its link, with changes applied to the target. Unmanaged functions or aliases with the same name, or an unrecognized wrapper, are preserved and stop setup. Existing Herdr configuration and session data are retained.

## Select an existing binary or rerun

```bash
bash install_herdr.sh --binary /absolute/path/to/herdr --dry-run
bash install_herdr.sh --binary /absolute/path/to/herdr
```

Replace the absolute path with your executable. The selected binary is not reinstalled. Rerunning with the same configuration reports that no change is needed. A new script can update the wrapper; update Herdr itself through Herdr's own procedure.

## Removal and validation

There is no dedicated uninstall option. Remove the managed block between its start and end markers in `~/.bashrc`, then open a new Bash session. Delete `~/.local/bin/herdr-open` only after confirming it is no longer used. Herdr itself and its session data need not be deleted.

```bash
python3 -m unittest discover -s tests -p 'test_install_herdr.py' -v
```

Tests use a temporary HOME and mocked Herdr/download behavior. They do not download the real application or open a real session.
