"""Optional portable MCP lifecycle with a host fixture; no real provider claim."""
import contextlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_ux_design_mcp import m,Client
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from agent_intelliforge import ux_port,runtime

class PortableDesignTests(unittest.TestCase):
    def fixture(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);home=Path(tmp.name);config={'owner':'test'};return home,config

    @contextlib.contextmanager
    def host(self,client):
        @contextlib.contextmanager
        def app():yield client
        with patch.object(runtime,'load',return_value=m),patch.object(m,'AppServer',app):yield

    def test_opt_in_repeat_and_update_do_not_adopt_or_restore_manual_services(self):
        home,config=self.fixture();client=Client()
        with self.host(client):
            self.assertEqual(ux_port.design_action(home,home,config,'install'),[]);self.assertEqual(client.calls,[])
            result=ux_port.design_action(home,home,config,'install',['figma']);self.assertTrue(result[0]['owned'])
            first=json.loads(json.dumps(config['design_mcp']))
            ux_port.design_action(home,home,config,'install',['figma']);self.assertEqual(config['design_mcp'],first)
            client.servers.clear();ux_port.design_action(home,home,config,'update',['whimsical']);self.assertEqual(client.servers,{})
        self.assertTrue((home/'settings.json').is_file())

    def test_connection_failure_records_retryable_state_and_keeps_core(self):
        home,config=self.fixture();config['installed']=True
        @contextlib.contextmanager
        def unavailable():raise m.MCPError('connection_failed');yield
        with patch.object(runtime,'load',return_value=m),patch.object(m,'AppServer',unavailable):
            result=ux_port.design_action(home,home,config,'install',['figma'])
        self.assertTrue(config['installed']);self.assertEqual(result[0]['status'],'incomplete');self.assertEqual(config['design_mcp_pending']['figma']['status'],'incomplete')
        with self.host(Client()):ux_port.design_action(home,home,config,'install',['figma'])
        self.assertEqual(config['design_mcp_pending'],{})

    def test_doctor_has_no_settings_writes_and_reports_auth_separately(self):
        home,config=self.fixture();client=Client({'figma':{'url':m.PROVIDERS['figma']}},auth='notLoggedIn')
        with self.host(client):result=ux_port.design_action(home,home,config,'doctor')
        self.assertEqual(next(r for r in result if r['provider']=='figma')['authentication'],'required');self.assertFalse((home/'settings.json').exists())

    def test_manual_disabled_provider_is_never_owned(self):
        home,config=self.fixture();client=Client({'my-figma':{'url':m.PROVIDERS['figma'],'enabled':False}})
        with self.host(client):ux_port.design_action(home,home,config,'install',['figma'])
        self.assertEqual(config['design_mcp'],{});self.assertFalse(client.servers['my-figma']['enabled'])

if __name__=='__main__':unittest.main()
