"""Claude implementation of the existing harness's structured-role protocol.

This module is invoked only inside explicit Claude portable runtimes. It does
not impersonate a Codex installation or change any personal agent settings.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .catalog import ForgeError
from .ownership import atomic_write
from .portable import capture, shell_command, native_command

REQUIRED_CLAUDE_FLAGS = ("--json-schema", "--output-format", "--allowedTools", "--strict-mcp-config", "--setting-sources")


def capabilities() -> dict:
    executable = shutil.which("claude")
    if not executable:
        return {"ready": False, "reason": "Claude Code CLI is not installed"}
    result = subprocess.run(native_command([executable, "--help"]), capture_output=True, text=True, encoding='utf-8', timeout=20)
    missing = [flag for flag in REQUIRED_CLAUDE_FLAGS if flag not in result.stdout]
    return {"ready": result.returncode == 0 and not missing, "missing": missing, "executable": executable}


def role_request(argv: list[str]) -> dict:
    boundary = argv.index("--") if "--" in argv else len(argv) - 1
    options, prompt = argv[:boundary], argv[boundary + 1:] if '--' in argv else argv[boundary:]
    if len(prompt) != 1:
        raise ForgeError("A structured role requires one literal prompt argument")
    def option(name, default=None):
        return options[options.index(name) + 1] if name in options else default
    schema_path, output = option("--output-schema"), option("--output-last-message")
    if not schema_path or not output:
        raise ForgeError("Structured role schema and output path are required")
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    configurations = []
    for index, argument in enumerate(options[:-1]):
        if argument == "-c": configurations.append(options[index + 1])
    images = [options[index + 1] for index, item in enumerate(options[:-1]) if item == "--image"]
    writable = [options[index + 1] for index, item in enumerate(options[:-1]) if item == "--add-dir"]
    network = not any(item == "sandbox_workspace_write.network_access=false" for item in configurations)
    return {"cwd": option("-C", os.getcwd()), "schema": schema, "schema_path": schema_path,
            "output": output, "prompt": sys.stdin.read() if prompt[0] == '-' else prompt[0], "mode": option("--sandbox", "read-only"),
            "model": option("--model"), "configurations": configurations, "images": images,
            "writable_directories": writable, "network": network}


def claude_command(request: dict, *, windows: bool | None = None) -> list[str]:
    windows = os.name == 'nt' if windows is None else windows
    if request["mode"] not in ("read-only", "workspace-write"):
        raise ForgeError("Unsupported permission mode; unrestricted execution is refused")
    tools = ["Read", "Grep", "Glob"]
    if not any(item.startswith("web_search=") and 'disabled' in item for item in request["configurations"]):
        tools += ["WebSearch", "WebFetch"]
    if request["mode"] == "workspace-write": tools += ["Edit", "Write", "PowerShell" if windows else "Bash"]
    prompt = request["prompt"]
    if request["images"]:
        prompt += "\nInspect these existing screenshot files with the Read tool:\n" + "\n".join(request["images"])
    command = ["claude", "-p", "--output-format", "json", "--json-schema",
               json.dumps(request["schema"], ensure_ascii=False, separators=(",", ":")),
               "--allowedTools", ",".join(tools + ["mcp__ux_gan_browser__*"]), "--tools", ",".join(tools),
               "--permission-mode", "default", "--setting-sources", "",
               "--settings", '{"disableAllHooks":true}', "--strict-mcp-config", "--no-session-persistence"]
    if request["model"]: command += ["--model", request["model"]]
    # Existing harness settings are TOML assignment values, not executable code.
    bridge = {}
    import tomllib
    for config in request["configurations"]:
        if config.startswith("mcp_servers.ux_gan_browser."):
            key, value = config.split("=", 1)
            field = key.rsplit(".", 1)[1]
            if field in ("command", "args", "env"):
                bridge[field] = tomllib.loads("value=" + value)["value"]
    if bridge:
        command += ["--mcp-config", json.dumps({"mcpServers": {"ux_gan_browser": bridge}})]
    else:
        command += ["--mcp-config", '{"mcpServers":{}}']
    return command


def role_environment(*, windows: bool | None = None) -> dict:
    value = os.environ.copy()
    windows = os.name == 'nt' if windows is None else windows
    if windows:
        value['CLAUDE_CODE_USE_POWERSHELL_TOOL'] = '1'
    return value


def structured_output(text: str) -> dict:
    value = json.loads(text)
    if not isinstance(value, dict) or value.get("is_error") is True or value.get("subtype", "success") != "success":
        raise ForgeError("Claude returned a failed or incomplete run")
    result = value.get("structured_output")
    if not isinstance(result, dict):
        raise ForgeError("Claude did not return structured_output; unstructured output is not accepted")
    return result


def isolated_command(argv: list[str], cwd: Path, writable: list[Path], network: bool, timeout=1800, state=None) -> list[str]:
    from .cli import state_root
    state = state or state_root()
    sdk = state / "claude/dependencies/mxc/node_modules/@microsoft/mxc-sdk/dist/v1/index.js"
    if not sdk.is_file():
        raise ForgeError("MXC runtime missing. Install a Claude experiment kit with --apply; isolation is never bypassed.")
    executables = [Path(shutil.which(name)).resolve().parent for name in ("claude", "node") if shutil.which(name)]
    profile = {"argv": native_command(argv), "cwd": str(cwd), "readonly": [str(path) for path in [cwd, Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")), Path(sys.prefix), Path(sys.base_prefix), Path(sys.executable).parent, state, *executables] if path.exists()],
               "writable": [str(path) for path in writable], "network": network, "timeoutMs": timeout * 1000,
               "sdk": str(sdk)}
    # Parent-only profile; no credentials or inherited environment are serialized.
    import tempfile
    directory = state / "claude/profiles"
    directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(suffix=".json", dir=directory)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(profile, stream)
    return ["node", str(Path(__file__).with_name("mxc-runner.mjs")), name]


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if "--help" in argv:
            check = capabilities()
            if not check["ready"]: raise ForgeError(str(check))
            print("Portable structured-role protocol: exec --json --output-schema --output-last-message --sandbox --ephemeral; sandbox -- command")
            return 0
        if "exec" in argv:
            request = role_request(argv)
            check = capabilities()
            if not check["ready"]: raise ForgeError(str(check))
            command = claude_command(request)
            writable = [Path(request["output"]).parent]
            if request["mode"] == "workspace-write":
                writable += [Path(request["cwd"]), *map(Path, request["writable_directories"])]
                writable += [Path(os.environ[name]) for name in ("TMPDIR", "TMP", "TEMP")
                             if os.environ.get(name) and Path(os.environ[name]).is_dir()]
            command = isolated_command(command, Path(request["cwd"]), writable, request["network"])
            prompt = request['prompt']
            if request['images']: prompt += '\nInspect screenshot files with Read:\n' + '\n'.join(request['images'])
            result = capture(command, cwd=request["cwd"], env=role_environment(), timeout=1800, input_text=prompt)
            if result["exit_code"] or result["timed_out"] or result["truncated"]:
                raise ForgeError("Claude isolated role failed: " + result["stderr"][-1000:])
            value = structured_output(result["stdout"])
            atomic_write(Path(request["output"]), (json.dumps(value, ensure_ascii=False) + "\n").encode())
            print(json.dumps({"type": "role.completed", "provider": "claude", "output": request["output"]}))
            return 0
        if "sandbox" in argv and "--" in argv:
            arguments = argv[argv.index("--") + 1:]
            if arguments == ["/bin/true"]: arguments = [sys.executable, "-c", "raise SystemExit(0)"]
            if len(arguments) > 2 and arguments[0] in ("/bin/bash", "bash") and arguments[1] == "-c":
                arguments = shell_command(arguments[2])
            readonly = any('sandbox_mode="read-only"' == item for item in argv)
            network = any("network_access=true" in item for item in argv)
            command = isolated_command(arguments, Path.cwd(), [] if readonly else [Path.cwd()], network)
            return subprocess.call(command)
        raise ForgeError("Unsupported harness operation for Claude; use Claude's native plugin manager for plugins")
    except (ForgeError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
