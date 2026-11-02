"""Scoped design MCP operations through the user's native Codex host."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from urllib.parse import urlparse

PROVIDERS={'whimsical':'https://mcp.whimsical.com/mcp','figma':'https://mcp.figma.com/mcp'}
FEATURES={
    'read':('fetch','get_design_context','get_metadata','get_screenshot','get_figjam'),
    'diagram':('generate_diagram','create_file','create','add_board_content'),
    'wireframe':('generate_wireframe','wireframe_edit','create_file','create','add_board_content','use_figma'),
    'edit':('edit','wireframe_edit','add_board_content','use_figma'),
    'layout':('auto_layout','wireframe_edit','use_figma'),
    'design_write':('use_figma',),
    'design_to_code':('get_design_context',),
    'code_to_design':('generate_figma_design','html_to_figma','send_code_to_figma'),
}

class MCPError(RuntimeError):
    def __init__(self,kind):self.kind=kind;super().__init__(kind)


def fingerprint(config):
    # OAuth login/refresh changes runtime status, never ownership of config.
    value={k:v for k,v in config.items() if k not in ('auth_status','authStatus','runtimeStatus','serverInfo')}
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def endpoint(config):return (config.get('url') or config.get('transport',{}).get('url') or '').rstrip('/')


class AppServer:
    """Bounded JSON-RPC client. Credentials and approvals stay in native Codex."""
    def __init__(self,codex_home=None,timeout=30):
        self.home=Path(codex_home or os.getenv('CODEX_HOME') or Path.home()/'.codex').expanduser().absolute()
        self.config_file=self.home/'config.toml';self.timeout=timeout;self.counter=0;self.messages=queue.Queue();self.threads={};self.closed=False
        try:self.process=subprocess.Popen(['codex','app-server','--stdio'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',env={**os.environ,'CODEX_HOME':str(self.home)})
        except OSError:raise MCPError('codex_unavailable') from None
        def reader():
            try:
                for line in self.process.stdout:
                    try:self.messages.put(json.loads(line))
                    except ValueError:self.messages.put({'transport_error':True})
            finally:self.messages.put({'transport_closed':True})
        self.reader=threading.Thread(target=reader,daemon=True);self.reader.start()
        try:
            self.rpc('initialize',{'clientInfo':{'name':'codex_ux_stack','title':'UX Stack','version':'1.4.0'},'capabilities':{}})
            self.send({'method':'initialized'})
        except BaseException:self.close();raise

    def send(self,value):
        try:self.process.stdin.write(json.dumps(value)+'\n');self.process.stdin.flush()
        except (OSError,BrokenPipeError):raise MCPError('connection_failed') from None

    def rpc(self,method,params):
        self.counter+=1;request_id=self.counter;self.send({'id':request_id,'method':method,'params':params});deadline=time.monotonic()+self.timeout
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise MCPError('timeout')
            try:value=self.messages.get(timeout=remaining)
            except queue.Empty:raise MCPError('timeout') from None
            if value.get('transport_error') or value.get('transport_closed'):raise MCPError('connection_failed')
            if 'method' in value and 'id' in value:
                # Never fabricate an OAuth response or silently approve tool work.
                raise MCPError('approval_required' if 'UserInput' in value['method'] or 'Approval' in value['method'] or 'elicitation' in value['method'] else 'unsupported_host_request')
            if value.get('method')=='mcpServer/startupStatus/updated' and value.get('params',{}).get('failureReason')=='reauthenticationRequired':raise MCPError('authentication_required')
            if value.get('id')!=request_id:continue
            if 'error' in value:
                code=value['error'].get('code');message=str(value['error'].get('message','')).lower()
                if code==-32601:raise MCPError('unsupported_host_api')
                if any(k in message for k in ('401','oauth','reauthentication','not logged')):raise MCPError('authentication_required')
                if any(k in message for k in ('403','permission','forbidden')):raise MCPError('permission_denied')
                if 'version' in message or 'conflict' in message:raise MCPError('configuration_changed')
                raise MCPError('host_request_failed')
            return value.get('result',{})

    def thread_for(self,name,servers):
        if name not in self.threads:
            overrides={'mcp_servers.'+key+'.enabled':key==name for key in servers}
            result=self.rpc('thread/start',{'ephemeral':True,'config':overrides})
            self.threads[name]=result['thread']['id']
        return self.threads[name]

    def close(self):
        if self.closed:return
        self.closed=True
        try:self.process.stdin.close()
        except OSError:pass
        try:self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.process.stdout.close();self.reader.join(timeout=1)

    def __enter__(self):return self
    def __exit__(self,*args):self.close()

def capability_matrix(tools, provider):
    if provider not in PROVIDERS:raise MCPError('unknown_provider')
    values=list(tools.values()) if isinstance(tools,dict) else tools
    valid={t.get('name'):t for t in values if isinstance(t,dict) and isinstance(t.get('name'),str) and isinstance(t.get('inputSchema'),dict)}
    result={}
    for feature,aliases in FEATURES.items():
        names=[name for name in aliases if name in valid]
        if feature=='wireframe':
            names=[n for n in names if n not in ('create_file','create','add_board_content') or 'wireframe' in json.dumps(valid[n],ensure_ascii=False).lower()]
        # Additional provider names remain discoverable. These are advertised
        # capabilities, never permission or successful execution claims.
        terms={'read':r'\b(read|fetch|get)\b.*\b(design|file|board|component)\b','diagram':r'\b(flowchart|diagram|user.flow)\b',
               'wireframe':r'\bwireframe\b','edit':r'\b(edit|update|modify)\b.*\b(canvas|board|design|shape|node)\b',
               'layout':r'\b(auto.layout|layout|rearrange)\b','design_write':r'\b(create|write|edit)\b.*\b(design|canvas)\b',
               'design_to_code':r'\bdesign.to.code\b','code_to_design':r'\bcode.to.design\b'}
        for name,tool in valid.items():
            text=(name.replace('_',' ')+' '+str(tool.get('description',''))).lower()
            if name not in names and re.search(terms[feature],text) and (feature=='read' or tool.get('annotations',{}).get('readOnlyHint') is not True):names.append(name)
        result[feature]={'available':bool(names),'tools':names,'verification':'advertised; target permission not tested'}
    return result

class DesignMCP:
    def __init__(self, client): self.client=client

    def configuration(self):
        response=self.client.rpc('config/read',{'includeLayers':True})
        servers=response.get('config',{}).get('mcp_servers') or {}
        if not isinstance(servers,dict):raise MCPError('invalid_configuration')
        version=response.get('version') # Older test/host adapters may expose it directly.
        target=str(getattr(self.client,'config_file',''))
        for layer in response.get('layers') or []:
            source=layer.get('name',{})
            if source.get('type')=='user' and (not target or str(source.get('file'))==target):version=layer.get('version')
        return servers,version

    def selection(self,provider,servers):
        if provider not in PROVIDERS:raise MCPError('unknown_provider')
        matches=[(name,cfg) for name,cfg in servers.items() if endpoint(cfg)==PROVIDERS[provider]]
        if len(matches)>1:raise MCPError('ambiguous_existing_registration')
        if matches:return matches[0]
        if provider in servers:raise MCPError('existing_name_conflict')
        return provider,None

    def register(self,provider,dry_run=False):
        servers,version=self.configuration();name,existing=self.selection(provider,servers)
        if existing is not None:return {'provider':provider,'name':name,'owned':False,'status':'existing' if existing.get('enabled',True) else 'disabled'}
        if dry_run:return {'provider':provider,'name':name,'owned':False,'status':'planned'}
        config={'url':PROVIDERS[provider]};params={'keyPath':'mcp_servers.'+name,'value':config,'mergeStrategy':'replace','expectedVersion':version}
        if hasattr(self.client,'config_file'):params['filePath']=str(self.client.config_file)
        self.client.rpc('config/value/write',params)
        after,_=self.configuration()
        if name not in after or endpoint(after[name])!=PROVIDERS[provider]:raise MCPError('registration_unverified')
        return {'provider':provider,'name':name,'owned':True,'status':'registered','sha256':fingerprint(after[name])}

    def diagnose(self,provider):
        result={'provider':provider,'registered':False,'connection':'not_configured','authentication':'not_tested','write_permission':'not_tested','ready':False,'capabilities':capability_matrix({},provider)}
        try:
            servers,_=self.configuration();name,config=self.selection(provider,servers)
            if config is None:return result
            result.update(registered=True,name=name)
            if not config.get('enabled',True):result['connection']='disabled';return result
            params={'serverName':name,'detail':'toolsAndAuthOnly','limit':100}
            if hasattr(self.client,'thread_for'):params['threadId']=self.client.thread_for(name,servers)
            tools={};auth='unknown';seen=set();status=None;tools_error=False
            for _ in range(20):
                response=self.client.rpc('mcpServerStatus/list',params)
                for item in response.get('data',[]):
                    if item.get('name')==name:
                        auth=item.get('authStatus','unknown');tools.update(item.get('tools') or {});status=item.get('runtimeStatus');tools_error=bool(item.get('toolsError'))
                cursor=response.get('nextCursor')
                if not cursor:break
                if cursor in seen:raise MCPError('incomplete_catalog')
                seen.add(cursor);params['cursor']=cursor
            else:raise MCPError('incomplete_catalog')
            result['authentication']='required' if auth=='notLoggedIn' else 'authenticated' if auth in ('oAuth','bearerToken') else 'unsupported' if auth=='unsupported' else 'unknown'
            result['runtime_status']=status
            result['connection']='authentication_required' if auth=='notLoggedIn' else 'catalog_failed' if tools_error else 'connected' if tools else 'not_verified'
            result['capabilities']=capability_matrix(tools,provider)
            result['ready']=result['connection']=='connected' and any(c['available'] for c in result['capabilities'].values())
            return result
        except MCPError as error:result['connection']=error.kind;return result

    def remove(self,component,dry_run=False):
        servers,_=self.configuration();name=component['name'];config=servers.get(name)
        if config is None:return {'status':'absent','name':name}
        if fingerprint(config)!=component.get('sha256'):raise MCPError('edited_configuration_preserved')
        if dry_run:return {'status':'planned','name':name}
        # Official remove only deletes this server registration; no logout/token deletion.
        env={**os.environ}
        if hasattr(self.client,'home'):env['CODEX_HOME']=str(self.client.home)
        try:r=subprocess.run(['codex','mcp','remove',name],capture_output=True,text=True,env=env,timeout=30)
        except (OSError,subprocess.TimeoutExpired):raise MCPError('remove_failed') from None
        if r.returncode:raise MCPError('remove_failed')
        after,_=self.configuration()
        if name in after:raise MCPError('remove_unverified')
        return {'status':'removed','name':name}

    def tools(self,provider):
        servers,_=self.configuration();name,config=self.selection(provider,servers)
        if not config or not config.get('enabled',True):raise MCPError('provider_unavailable')
        thread=self.client.thread_for(name,servers)
        params={'serverName':name,'threadId':thread,'detail':'toolsAndAuthOnly','limit':100};tools={};seen=set();found=False
        for _ in range(20):
            response=self.client.rpc('mcpServerStatus/list',params)
            for item in response.get('data',[]):
                if item.get('name')!=name:continue
                found=True
                if item.get('authStatus')=='notLoggedIn':raise MCPError('authentication_required')
                if item.get('toolsError'):raise MCPError('catalog_failed')
                tools.update(item.get('tools') or {})
            cursor=response.get('nextCursor')
            if not cursor:break
            if cursor in seen:raise MCPError('incomplete_catalog')
            seen.add(cursor);params['cursor']=cursor
        else:raise MCPError('incomplete_catalog')
        if not found:raise MCPError('incomplete_catalog')
        return name,thread,tools

    def call(self,provider,tool,arguments,target,apply=False):
        """Only a declared file target; schema discovery never grants write access."""
        name,thread,tools=self.tools(provider)
        if tool not in tools:raise MCPError('tool_unavailable')
        if not isinstance(target,dict) or not isinstance(target.get('file_id'),str) or not target['file_id']:raise MCPError('target_required')
        file_id=target['file_id'];url=target.get('url','');parsed=urlparse(url)
        allowed=('figma.com','www.figma.com') if provider=='figma' else ('whimsical.com','www.whimsical.com')
        parts=parsed.path.strip('/').split('/')
        bound=(len(parts)>1 and parts[0] in ('design','file','board','proto') and parts[1]==file_id) if provider=='figma' else (bool(parts) and (parts[-1]==file_id or parts[-1].endswith('-'+file_id)))
        if parsed.scheme!='https' or parsed.hostname not in allowed or parsed.username or parsed.password or not bound:raise MCPError('invalid_target')
        if not isinstance(arguments,dict):raise MCPError('invalid_arguments')
        def targets(value):
            if isinstance(value,dict):
                for key,item in value.items():
                    if key in ('fileKey','file_id','fileId','fileUrl','url','boardId','board_id'):yield item
                    else:yield from targets(item)
            elif isinstance(value,list):
                for item in value:yield from targets(item)
        bindings=list(targets(arguments))
        if not bindings or any(str(v) not in (file_id,url) for v in bindings):raise MCPError('target_mismatch')
        read_only=tools[tool].get('annotations',{}).get('readOnlyHint') is True
        if not read_only and not apply:raise MCPError('explicit_apply_required')
        # Arbitrary code may access more nodes than its envelope suggests. Use
        # the host's Figma skill for code-based canvas work, then import a snapshot.
        def code(value):
            if isinstance(value,dict):return any(k in ('code','javascript','script') or code(v) for k,v in value.items())
            return any(code(v) for v in value) if isinstance(value,list) else False
        if tool=='use_figma' or code(arguments):raise MCPError('use_host_skill_for_code_tools')
        schema=tools[tool].get('inputSchema',{})
        if any(k not in arguments for k in schema.get('required',[])):raise MCPError('missing_tool_argument')
        result=self.client.rpc('mcpServer/tool/call',{'threadId':thread,'server':name,'tool':tool,'arguments':arguments})
        if result.get('isError'):
            # Classify without copying provider content (which can contain a
            # private document or credential) into diagnostics or install logs.
            message=json.dumps(result,ensure_ascii=False).lower()
            if any(word in message for word in ('401','oauth','authentication required','not logged')):raise MCPError('authentication_required')
            if any(word in message for word in ('403','permission','forbidden','access denied')):raise MCPError('permission_denied')
            raise MCPError('provider_tool_failed')
        return {'provider':provider,'tool':tool,'file_id':file_id,'result':result,
                'permission_verified':'read' if read_only else 'not_verified',
                'operation_status':'read_succeeded' if read_only else 'call_accepted',
                'write_effect':'not_applicable' if read_only else 'not_verified; reread the target and compare revision/content'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('doctor','catalog','call'));parser.add_argument('--providers',default='whimsical,figma');parser.add_argument('--codex-home');parser.add_argument('--request',type=Path);parser.add_argument('--apply',action='store_true');parser.add_argument('--timeout',type=int,default=30)
    a=parser.parse_args(argv);providers=list(dict.fromkeys(a.providers.split(',')))
    if not providers or any(p not in PROVIDERS for p in providers):parser.error('providers must be whimsical,figma')
    with AppServer(a.codex_home,a.timeout) as client:
        service=DesignMCP(client)
        if a.command=='doctor':result={'providers':[service.diagnose(p) for p in providers]}
        elif a.command=='catalog':
            result={'providers':[]}
            for p in providers:
                name,_,tools=service.tools(p);result['providers'].append({'provider':p,'name':name,'tools':tools})
        else:
            if not a.request or len(providers)!=1:parser.error('call requires --request and one provider')
            if a.request.is_symlink() or a.request.stat().st_size>2_000_000:raise MCPError('unsafe_request')
            request=json.loads(a.request.read_text(encoding='utf-8'));result=service.call(providers[0],request['tool'],request['arguments'],request['target'],a.apply)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (MCPError,OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as error:
        print(json.dumps({'status':'unavailable','reason':error.kind if isinstance(error,MCPError) else 'invalid_input_or_transport'}));raise SystemExit(1)
