from pathlib import Path
import copy
import importlib.util
import unittest
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ux_design_mcp_test',ROOT/'tools/codex-ux-stack/ux-visual-design/scripts/design_mcp.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Client:
    def __init__(self,servers=None,auth='oAuth',tools=None):
        self.servers=servers or {};self.calls=[];self.auth=auth;self.tools=tools or {}
    def rpc(self,method,params):
        self.calls.append((method,copy.deepcopy(params)))
        if method=='config/read':return {'config':{'mcp_servers':self.servers},'layers':[{'name':{'type':'user','file':'fixture/config.toml'},'version':'v1'}]}
        if method=='config/value/write':
            name=params['keyPath'].split('.')[-1];self.servers[name]=params['value'];return {'version':'v2'}
        if method=='mcpServerStatus/list':return {'data':[{'name':params['serverName'],'authStatus':self.auth,'tools':self.tools,'resources':[],'resourceTemplates':[]}], 'nextCursor':None}
        raise AssertionError(method)

class DesignMCPTests(unittest.TestCase):
    def test_selection_deduplicates_existing_url_without_adopting_manual_configuration(self):
        c=Client({'custom-figma':{'url':'https://mcp.figma.com/mcp','enabled':True,'tool_timeout_sec':99}})
        result=m.DesignMCP(c).register('figma')
        self.assertEqual(result['name'],'custom-figma');self.assertFalse(result['owned'])
        self.assertFalse(any(method.endswith('/write') for method,_ in c.calls))

    def test_explicit_registration_is_targeted_and_dry_run_never_writes(self):
        c=Client();result=m.DesignMCP(c).register('whimsical',dry_run=True)
        self.assertEqual(result['status'],'planned');self.assertEqual(c.servers,{})
        result=m.DesignMCP(c).register('whimsical')
        self.assertTrue(result['owned']);self.assertEqual(set(c.servers),{'whimsical'})
        writes=[p for method,p in c.calls if method=='config/value/write']
        self.assertEqual(writes[0]['expectedVersion'],'v1')
        self.assertEqual(writes[0]['value'],{'url':'https://mcp.whimsical.com/mcp'})

    def test_disabled_manual_registration_is_not_reenabled_or_duplicated(self):
        c=Client({'figma':{'url':'https://mcp.figma.com/mcp','enabled':False}})
        result=m.DesignMCP(c).register('figma')
        self.assertEqual(result['status'],'disabled');self.assertFalse(result['owned'])
        self.assertFalse(c.servers['figma']['enabled'])

    def test_runtime_catalog_handles_old_and_current_creation_names(self):
        old={'generate_wireframe':{'name':'generate_wireframe','inputSchema':{'type':'object'}}}
        new={'create_file':{'name':'create_file','description':'Create a wireframe or board','inputSchema':{'type':'object'}},
             'wireframe_edit':{'name':'wireframe_edit','inputSchema':{'type':'object'}}}
        self.assertEqual(m.capability_matrix(old,'whimsical')['wireframe']['tools'],['generate_wireframe'])
        self.assertIn('create_file',m.capability_matrix(new,'whimsical')['wireframe']['tools'])
        self.assertFalse(m.capability_matrix({},'figma')['design_write']['available'])

    def test_diagnostics_keep_auth_capabilities_and_permission_separate(self):
        c=Client({'figma':{'url':'https://mcp.figma.com/mcp'}},auth='notLoggedIn')
        result=m.DesignMCP(c).diagnose('figma')
        self.assertEqual(result['authentication'],'required');self.assertEqual(result['write_permission'],'not_tested')
        self.assertFalse(result['ready']);self.assertEqual(result['provider'],'figma')

    def test_configuration_auth_refresh_does_not_change_ownership_fingerprint(self):
        config={'url':'https://mcp.figma.com/mcp','authStatus':'notLoggedIn'}
        other={**config,'authStatus':'oAuth','runtimeStatus':{'status':'connected'}}
        self.assertEqual(m.fingerprint(config),m.fingerprint(other))


@unittest.skipUnless(os.environ.get('UX_NATIVE_MCP_TESTS')=='1','Opt-in real Codex host with a local fixture; no provider OAuth')
class NativeCodexMCPTests(unittest.TestCase):
    def test_real_host_registers_lists_and_reads_local_mcp_without_model_or_user_settings(self):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):self.send_response(405);self.end_headers()
            def do_DELETE(self):self.send_response(204);self.end_headers()
            def do_POST(self):
                request=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
                calls.append(request['method'])
                if 'id' not in request:self.send_response(202);self.end_headers();return
                method=request['method']
                if method=='initialize':result={'protocolVersion':request['params']['protocolVersion'],'capabilities':{'tools':{}},'serverInfo':{'name':'local-design-fixture','version':'1'}}
                elif method=='tools/list':result={'tools':[{'name':'fetch','description':'Read the named test design','inputSchema':{'type':'object','properties':{'file_id':{'type':'string'}},'required':['file_id']},'annotations':{'readOnlyHint':True}}]}
                elif method=='tools/call':result={'content':[{'type':'text','text':'A human changed the test title'}],'structuredContent':{'file_id':'fixture123','title':'Updated title'}}
                else:result={}
                data=json.dumps({'jsonrpc':'2.0','id':request['id'],'result':result}).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        old=m.PROVIDERS['figma'];m.PROVIDERS['figma']=f'http://127.0.0.1:{server.server_port}/mcp'
        try:
            with tempfile.TemporaryDirectory(prefix='ux-native-design-') as td:
                root=Path(td);config=root/'config.toml';config.write_text('# Preserve this user comment\nmodel = "gpt-6.1-sol"\n')
                with m.AppServer(root,30) as client:
                    service=m.DesignMCP(client);registration=service.register('figma')
                    self.assertTrue(registration['owned']);self.assertIn('# Preserve this user comment',config.read_text())
                    self.assertEqual(service.register('figma')['status'],'existing')
                    diagnosis=service.diagnose('figma');self.assertTrue(diagnosis['capabilities']['read']['available'],diagnosis)
                    result=service.call('figma','fetch',{'file_id':'fixture123'},{'file_id':'fixture123','url':'https://www.figma.com/design/fixture123/Fixture'})
                    self.assertEqual(result['result']['structuredContent']['title'],'Updated title')
                    self.assertEqual(service.remove(registration)['status'],'removed')
                self.assertIn('tools/list',calls);self.assertIn('tools/call',calls)
                self.assertNotIn('mcp_servers',config.read_text())
        finally:
            m.PROVIDERS['figma']=old;server.shutdown();server.server_close();thread.join(timeout=5)

if __name__=='__main__':unittest.main()
