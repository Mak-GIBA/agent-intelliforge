"""User-scoped SpecKit companion. No agent hooks or model calls."""
VERSION = '2.1.0'
SPECIFY_PIN = '1.0.8'

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
