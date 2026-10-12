#!/usr/bin/env python3
"""Rebuild the standalone Herdr entry without changing its Bash behavior."""
from pathlib import Path
import argparse
ROOT=Path(__file__).resolve().parent
if __name__ == '__main__':
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
 content=(ROOT/'bootstrap.sh.in').read_text().replace('@INSTALLER_SOURCE@',(ROOT/'install.py').read_text().rstrip('\n'))
 target=ROOT.parents[1]/'install_herdr.sh'
 if a.check:
  if target.read_text()!=content:p.exit(1,'Standalone Herdr differs from source.\n')
 else:target.write_text(content)
 print(('Checked ' if a.check else 'Built ')+target.name)
