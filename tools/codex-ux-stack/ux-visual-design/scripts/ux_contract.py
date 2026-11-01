"""Local UX contracts and editable design exchange; no network or model calls."""
from __future__ import annotations

class ContractError(ValueError):
    pass

def validate(contract, project=None):
    raise NotImplementedError('UX contract validation')

def reconcile(base, local, remote):
    raise NotImplementedError('Three-way design reconciliation')

def render_bundle(contract, destination):
    raise NotImplementedError('Editable UX visualization')

def import_design(contract, source):
    raise NotImplementedError('Human-edited design import')
