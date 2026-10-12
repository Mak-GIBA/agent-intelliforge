#!/usr/bin/env python3
from workbench.cli import main

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__ == '__main__':
    raise SystemExit(main())
