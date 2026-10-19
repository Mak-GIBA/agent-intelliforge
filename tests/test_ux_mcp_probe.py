"""Real stdio subprocess failures; no model, downloads or browser installation."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT/'tools/codex-ux-stack/skill/scripts/mcp-probe.cjs'
BRIDGE = r'''
const readline=require('node:readline');
const lines=readline.createInterface({input:process.stdin});
lines.on('line',line=>{
 const req=JSON.parse(line);if(req.id===undefined)return;
 if(process.env.PROBE_CASE==='malformed'){console.log('not-json');return;}
 let result;
 if(req.method==='initialize')result={capabilities:{tools:{}}};
 else if(req.method==='tools/list')result={tools:process.env.PROBE_CASE==='missing'?[]:['ux_navigate','ux_fill','ux_click'].map(name=>({name}))};
 else result={isError:true,content:[{type:'text',text:process.env.PROBE_CASE==='permission'?'EROFS read-only file system':'Chromium launch failed'}]};
 console.log(JSON.stringify({jsonrpc:'2.0',id:req.id,result}));
});
'''


@unittest.skipUnless(shutil.which('node'), 'Node is required for stdio MCP contract tests')
class ProbeTests(unittest.TestCase):
    def probe(self, case):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            shutil.copy2(PROBE,root/'mcp-probe.cjs')
            (root/'visual-browser.cjs').write_text(BRIDGE,encoding='utf-8')
            return subprocess.run(['node',str(root/'mcp-probe.cjs')],capture_output=True,text=True,
                                  env=dict(os.environ,PROBE_CASE=case,UX_GAN_SCREENSHOTS=str(root/'images')),timeout=10)

    def test_missing_tools_are_reported_before_browser_launch(self):
        result=self.probe('missing')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('tools/list',result.stderr)
        self.assertIn('MCP tool missing',result.stderr)

    def test_permission_failure_keeps_stage_and_original_error(self):
        result=self.probe('permission')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('ux_navigate',result.stderr)
        self.assertIn('EROFS',result.stderr)

    def test_malformed_handshake_is_not_ready(self):
        result=self.probe('malformed')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('initialize',result.stderr)

    def test_chromium_launch_failure_is_distinct_from_a_missing_tool(self):
        result=self.probe('browser')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Chromium launch failed',result.stderr)
        self.assertNotIn('MCP tool missing',result.stderr)
