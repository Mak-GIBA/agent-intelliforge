# Open Herdr for a directory

**English** | [日本語](../../herdr/usage.md)

[Overview](README.md) · [Installation](installation.md)

## Daily use

In Bash with the configuration loaded, move into your project and run:

```bash
cd /path/to/project
herdr
```

Replace `/path/to/project` with your directory. Without arguments, `herdr` starts a server only if needed and selects the current directory's workspace. If none exists, it creates one for that directory. From inside Herdr, it switches the existing UI instead of opening another client.

To select a directory explicitly or use the original CLI:

```bash
herdr-open /path/to/project
herdr --version
herdr workspace list
```

Arguments to `herdr` are passed to the original binary. `herdr-open` requires an interactive terminal; it is not intended to open a UI from automation.

## Workspace matching

The wrapper compares the selected session's `session.json` with the running workspace list. It saves the initial real-path association in `herdr-open-workspaces.json` inside the session directory, without modifying `session.json`. Matching labels alone do not justify reusing or switching a workspace to another directory.

Startup logs are written to `herdr-open-startup.log` in the same directory. Startup, lock acquisition, and snapshot matching each wait up to 15 seconds. For unknown formats or matching failures, inspect the reported cause and logs. Later changes to the working directory do not silently replace the initially recorded association.
