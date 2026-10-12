"""Compact document routing; legacy projects keep their existing layout."""
from __future__ import annotations

COMPACT = 'compact-v1'
DOCUMENTS = ('requirements.md', 'design.md', 'verification.md')


def compact(config: dict) -> bool:
    return config.get('document_layout') == COMPACT


def destination(kind: str) -> str:
    if kind in {'design', 'decision'}:
        return 'design.md'
    if kind in {'verification', 'evidence'}:
        return 'verification.md'
    return 'requirements.md'


def internal(config: dict, legacy: str, name: str) -> str:
    return '.specify/workbench/' + name if compact(config) else config['docs_dir'] + '/' + legacy

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
