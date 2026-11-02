"""Scoped design MCP operations through the user's native Codex host."""
class MCPError(RuntimeError):
    pass

def capability_matrix(tools, provider):
    raise NotImplementedError('Live capability discovery')

class DesignMCP:
    def __init__(self, client): self.client=client
    def register(self,provider,dry_run=False): raise NotImplementedError('Owned optional registration')
    def diagnose(self,provider): raise NotImplementedError('Separated MCP diagnostics')
