"""Standalone child-role policy; also shipped in the research bundle."""
from __future__ import annotations

import os
import json
from pathlib import Path
import re

MODES = ("read-only", "workspace-write")


def role_sandbox(state, role):
    if role == "fixer":
        return "workspace-write"
    mode = state.get("role_runtime", {}).get("sandbox", state["config"].get("role_sandbox", "read-only"))
    if mode not in MODES:
        raise ValueError("Unsupported role sandbox: " + str(mode))
    return mode


def override_sandbox(state, mode, timestamp):
    """Keep frozen config/checkpoint hashes intact when resuming an old run."""
    if mode is None:
        return
    if mode not in MODES:
        raise ValueError("Unsupported role sandbox: " + str(mode))
    previous = role_sandbox(state, "reviewer")
    if previous != mode:
        state.setdefault("role_runtime_history", []).append({
            "previous": previous, "sandbox": mode, "changed_at": timestamp})
        state["role_runtime"] = {"sandbox": mode}


def child_environment(directory, marker):
    """Preserve authentication/configuration; isolate only transient tool state."""
    root = Path(directory).resolve() / ".runtime"
    paths = {name: root / name for name in ("tmp", "cache", "uv", "npm")}
    for path in paths.values():
        if path.is_symlink():
            raise ValueError("Refusing a symlink runtime directory: " + str(path))
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = dict(os.environ)
    env[marker] = "1"
    for name in ("TMPDIR", "TMP", "TEMP"):
        env[name] = str(paths["tmp"])
    for name, path in (("XDG_CACHE_HOME", "cache"), ("UV_CACHE_DIR", "uv"), ("npm_config_cache", "npm")):
        env.setdefault(name, str(paths[path]))
    return env


def failure_kind(text):
    """Classify observed errors conservatively; unknown failures never retry."""
    text = text.lower()
    if "requires approval" in text or "approval policy" in text:
        return "tool_approval"
    if "model" in text and re.search(r"at capacity|rate.limit|\b429\b", text):
        return "model_capacity"
    if re.search(r"rate.limit|\b429\b", text):
        return "rate_limit"
    if re.search(r"stream disconnected|connection.*model", text):
        return "model_connection"
    if re.search(r"unauthenticated|unauthorized|authentication|invalid.api.key|login.required|401\b|403\b", text):
        return "authentication"
    if "evidence_write" in text or "browser evidence write failed" in text:
        return "evidence_write"
    if re.search(r"(listen|connect|socket).*?(eperm|eacces|permission denied)", text):
        return "network_permission"
    browser = bool(re.search(r"playwright|chromium|ux_gan_browser|browser", text))
    if browser and re.search(r"eacces|erofs|eperm|permission denied|operation not permitted|read.only file system", text):
        return "browser_permission"
    if browser and re.search(r"timed.out|timeout", text):
        return "browser_timeout"
    if browser and re.search(r"launch|sandbox|executable.*(missing|exist)|failed to start", text):
        return "browser_launch"
    if browser and re.search(r"mcp|initializ|handshake|connect|unavailable|not available", text):
        return "browser_mcp"
    if re.search(r"eacces|erofs|permission denied|read.only file system", text):
        return "permission"
    if re.search(r"timed.out|timeout", text):
        return "timeout"
    if re.search(r"mcp.*(failed|error|initializ|handshake)", text):
        return "mcp_initialization"
    return "execution"


def browser_failure(kind):
    return kind in {"browser_permission", "browser_timeout", "browser_launch", "browser_mcp"}


def event_errors(path):
    """Prefer terminal CLI errors over earlier tool failures or successful events."""
    terminal, errors, tools, stderr = [], [], [], []
    path = Path(path)
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 1024 * 1024))
        text = stream.read().decode("utf-8", "replace")
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "turn.failed":
            error = event.get("error", {})
            terminal.append(str(error.get("message", error) if isinstance(error, dict) else error))
        elif event.get("type") == "error":
            errors.append(str(event.get("message", "")))
        elif "stderr" in event:
            stderr.append(str(event["stderr"]))
        item = event.get("item", {})
        if isinstance(item, dict) and item.get("type") == "mcp_tool_call" and item.get("status") == "failed":
            error = item.get("error", {})
            message = error.get("message", error) if isinstance(error, dict) else error
            tools.append("MCP " + str(item.get("server", "")) + ": " + str(message))
    return "\n".join(terminal or errors or tools or stderr)[-16000:]
