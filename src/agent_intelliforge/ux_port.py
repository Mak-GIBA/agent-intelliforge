"""Optional Codex UX design MCP ownership; failure does not roll back the Core kit."""
from __future__ import annotations
import json
from .catalog import ForgeError
from .ownership import atomic_write

def design_action(home,bundle,config,action,selected=()):
    from .runtime import load
    owned=config.setdefault('design_mcp',{})
    providers=list(dict.fromkeys([*selected,*owned]))
    if action=='doctor' and not providers:providers=['whimsical','figma']
    if not providers:return []
    module=load(bundle/'ux-visual-design/scripts/design_mcp.py','_intelliforge_design_mcp')
    def save():atomic_write(home/'settings.json',(json.dumps(config,ensure_ascii=False,indent=2)+'\n').encode())
    results=[]
    try:
        with module.AppServer() as client:
            service=module.DesignMCP(client)
            for provider in providers:
                component=owned.get(provider)
                try:
                    if action=='doctor':results.append(service.diagnose(provider));continue
                    if action=='uninstall':
                        if component:results.append({'provider':provider,**service.remove(component)});owned.pop(provider,None);save()
                        continue
                    if action=='update' and not component:
                        results.append({'provider':provider,'status':'unmanaged_preserved'});continue
                    if component:
                        servers,_=service.configuration();current=servers.get(component['name'])
                        if action=='update' and (not current or not current.get('enabled',True)):
                            results.append({'provider':provider,'status':'removed_or_disabled_preserved'});continue
                        if current and module.fingerprint(current)!=component['sha256']:raise module.MCPError('edited_configuration_preserved')
                    config.setdefault('design_mcp_pending',{})[provider]={'status':'checking','url':module.PROVIDERS[provider]};save()
                    result=service.register(provider)
                    if result['owned']:owned[provider]={k:result[k] for k in ('provider','name','sha256')}
                    elif not component:config.setdefault('design_mcp_references',{})[provider]={'name':result['name'],'owned':False,'status':result['status']}
                    config['design_mcp_pending'].pop(provider,None);save();results.append(result)
                except (module.MCPError,OSError,ValueError):
                    if action=='uninstall':raise ForgeError('Edited or unavailable design MCP preserved; Core resources retained') from None
                    config.setdefault('design_mcp_pending',{})[provider]={'status':'incomplete'};save()
                    results.append({'provider':provider,'status':'incomplete','reason':'configuration_or_transport','core_retained':True})
    except module.MCPError as error:
        if action=='uninstall':raise ForgeError('Design MCP unavailable; owned Core resources retained') from None
        if action=='doctor':return [{'provider':p,'ready':False,'connection':error.kind,'authentication':'not_tested','write_permission':'not_tested'} for p in providers]
        config.setdefault('design_mcp_pending',{}).update({p:{'status':'incomplete'} for p in providers});save()
        return [{'provider':p,'status':'incomplete','reason':error.kind,'core_retained':True} for p in providers]
    return results
