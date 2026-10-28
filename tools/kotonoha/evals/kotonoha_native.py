import importlib.util,json,os,sys,tempfile,shutil
from pathlib import Path
import argparse
p=argparse.ArgumentParser(description='Isolated native Skill invocation checks')
p.add_argument('--study',type=Path,required=True);p.add_argument('--upstream-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'tools/kotonoha/evals'))
import run_study as base
contract=json.loads((a.study/'contract.json').read_text())
disabled=base.globals_to_disable()
source=a.upstream_source
for ident,prefix in [('natural',''),('explicit','$kotonoha '),('legacy','$yomiyasu ')]:
 out=a.out/(ident+'.json')
 if out.exists():continue
 with tempfile.TemporaryDirectory(prefix='kotonoha-native-') as td:
  cwd=Path(td);skills=cwd/'.agents/skills'
  spec=importlib.util.spec_from_file_location('native_kt',repo/'tools/kotonoha/installer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  scan=m.conflict_scan
  def isolated(target,project=None):
   result=scan(target,project);result['duplicate_skill']=[p for p in result['duplicate_skill'] if str((Path(p)/'SKILL.md').resolve()) not in disabled];return result
  m.conflict_scan=isolated
  m.install_selected(skills,m.COMPONENTS,mode='auto',apply=True,source=source,project=cwd)
  sample=cwd/'article.md';sample.write_text('# 設定の保持\n\n起動時の設定保持は処理の効率化につながる。適切な更新管理が重要となる。\n\n素材：従来は要求ごとに設定ファイルを読む。提案方式は起動時に読み込み、要求時はメモリ上の値を使う。ファイルを編集しても保持した値は変わらず、再起動で読み直す。時間は未測定。\n',encoding='utf-8')
  prompt=prefix+'article.mdを新任担当者向けに推敲してください。素材も本文へ統合し、何が変わるかと必要な操作を説明してください。条件と未測定という事実は保持し、完成稿をarticle.mdに保存してください。'
  result=base.execute(prompt,cwd,contract,disabled,native=True)
  result['text']=sample.read_text(encoding='utf-8');result['route']=ident
  result['asset_sha256']={p.relative_to(repo/'tools/kotonoha/assets').as_posix():base.sha(p.read_bytes()) for p in (repo/'tools/kotonoha/assets').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
  out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print(ident,result['status'],len(result['tools']),flush=True)
