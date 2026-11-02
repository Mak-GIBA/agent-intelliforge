from pathlib import Path
import copy
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ux_design_mcp_test',ROOT/'tools/codex-ux-stack/ux-visual-design/scripts/design_mcp.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Client:
    def __init__(self,servers=None,auth='oAuth',tools=None):
        self.servers=servers or {};self.calls=[];self.auth=auth;self.tools=tools or {}
    def rpc(self,method,params):
        self.calls.append((method,copy.deepcopy(params)))
        if method=='config/read':return {'config':{'mcp_servers':self.servers},'version':'v1'}
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

if __name__=='__main__':unittest.main()
