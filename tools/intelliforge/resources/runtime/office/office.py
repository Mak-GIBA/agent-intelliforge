#!/usr/bin/env python3
"""OfficeCLI adapter + conservative local document utilities. Not an Office renderer."""
from __future__ import annotations
import argparse
import collections
import contextlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import time
import tomllib
import zipfile
import xml.etree.ElementTree as ET

from common import OfficeError, absolute, atomic_write, file_sha, json_bytes, load_json, lock, new_file, no_symlinks, office_env, paths, run, sha

ROOT=Path(__file__).resolve().parent
SUPPORTED={'.pdf','.docx','.pptx'}
MAX_INPUT=100*1024*1024
MAX_UNPACKED=300*1024*1024
MCP_NAME='codex-office-workbench'


def source_file(value):
    p=absolute(value)
    no_symlinks(p)
    if not p.is_file():raise OfficeError(f'File not found: {p}')
    if p.suffix.lower() not in SUPPORTED:
        raise OfficeError('Supported: .pdf .docx .pptx. Legacy .doc/.ppt, macro-enabled files, and spreadsheets are outside this Skill.')
    if p.stat().st_size>MAX_INPUT:raise OfficeError('Input exceeds 100 MiB; split or use an isolated reviewed workflow')
    return p


def safe_zip(p):
    z=zipfile.ZipFile(p)
    try:
        seen=set();total=0
        if len(z.infolist())>10000:raise OfficeError('Too many ZIP entries')
        for info in z.infolist():
            rel=PurePosixPath(info.filename)
            if info.filename in seen or rel.is_absolute() or '..' in rel.parts or '\\' in info.filename:
                raise OfficeError('Unsafe/duplicate OOXML member')
            seen.add(info.filename)
            total+=info.file_size
            if info.flag_bits & 1:raise OfficeError('Encrypted ZIP entries are not supported')
            if info.file_size>60*1024*1024 or total>MAX_UNPACKED:
                raise OfficeError('OOXML uncompressed size limit exceeded')
            if info.file_size>1024*1024 and info.file_size>max(info.compress_size,1)*1000:
                raise OfficeError('Suspicious compression ratio')
            if 'vbaproject' in info.filename.lower() or info.filename.lower().endswith('.bin') and 'vba' in info.filename.lower():
                raise OfficeError('Macros are not supported; do not execute this document')
        required='word/document.xml' if p.suffix.lower()=='.docx' else 'ppt/presentation.xml'
        if required not in seen or '[Content_Types].xml' not in seen:
            raise OfficeError('File does not contain the expected Office structure')
        for name in seen:
            if name.endswith(('.xml','.rels')):
                b=z.read(name)
                if b'<!DOCTYPE' in b.replace(b'\x00',b'').upper() or b'<!ENTITY' in b.replace(b'\x00',b'').upper():
                    raise OfficeError('DOCTYPE/entity declarations are not allowed')
                # Well-formedness only; OfficeCLI validate checks schema later.
                ET.fromstring(b)
        return z
    except BaseException:
        z.close();raise


def facts(p):
    p=source_file(p)
    r={'path':str(p),'sha256':file_sha(p),'bytes':p.stat().st_size,'format':p.suffix[1:].lower(),
       'warnings':[],'checks':{'visual_review':'NOT_PERFORMED'}}
    if p.suffix.lower()=='.pdf':
        from pypdf import PdfReader
        reader=PdfReader(p)
        if reader.is_encrypted:raise OfficeError('Encrypted PDF: use a separately approved decryption workflow')
        r['pages']=len(reader.pages)
        r['page_sizes']=[{'width':float(x.mediabox.width),'height':float(x.mediabox.height)} for x in reader.pages]
        r['warnings'].append('Page count/structure is not text accuracy, signature validity, or visual verification.')
        return r
    with safe_zip(p) as z:
        r['parts']={i.filename:sha(z.read(i.filename)) for i in z.infolist() if not i.is_dir()}
        r['media']={n:h for n,h in r['parts'].items() if '/media/' in n}
        r['external_relations']=[];r['fonts']=[]
        for n in r['parts']:
            if n.endswith('.rels'):
                for el in ET.fromstring(z.read(n)):
                    if el.get('TargetMode')=='External':
                        r['external_relations'].append({'part':n,'type':el.get('Type','').rsplit('/',1)[-1],
                                                        'target':el.get('Target','')})
            if n.endswith('.xml'):
                for el in ET.fromstring(z.read(n)).iter():
                    if el.tag.rsplit('}',1)[-1]=='rFonts':
                        r['fonts'] += list(el.attrib.values())
                    if el.tag.rsplit('}',1)[-1] in ('latin','ea','cs') and el.get('typeface'):
                        r['fonts'].append(el.get('typeface'))
        r['fonts']=sorted(set(r['fonts']))
        if r['format']=='pptx':
            doc=ET.fromstring(z.read('ppt/presentation.xml'))
            r['slides']=sum(1 for e in doc.iter() if e.tag.endswith('}sldId'))
        else:
            doc=ET.fromstring(z.read('word/document.xml'))
            r['paragraphs']=sum(1 for e in doc.iter() if e.tag.endswith('}p'))
            r['tables']=sum(1 for e in doc.iter() if e.tag.endswith('}tbl'))
            r['pages']=None
            r['warnings'].append('DOCX pages are renderer-dependent; not inferred from paragraph count.')
        if any('/embeddings/' in n for n in r['parts']):r['warnings'].append('Contains embedded objects; do not execute them.')
        if any('signature' in n.lower() for n in r['parts']):r['warnings'].append('Editing may invalidate digital signatures.')
    return r


def assert_render_safe(info):
    # Hyperlink text is not automatically fetched. Remote images/templates must not be resolved automatically.
    unsafe=[x for x in info.get('external_relations',[]) if x.get('type')!='hyperlink']
    if unsafe:raise OfficeError('External image/template/data links detected. Resolve with consent in an isolated workflow before conversion.')


def config():
    p=paths();d=load_json(p['config'])
    if d.get('owner')!='codex-office-workbench':raise OfficeError('Unrecognized install manifest')
    return d


def office_binary(d):
    value=d.get('officecli',{}).get('path')
    if not value:raise OfficeError('OfficeCLI is not installed (assets-only). Re-run installer --apply --force.')
    p=absolute(value)
    if not p.is_file():raise OfficeError('Configured OfficeCLI is missing')
    if file_sha(p)!=d['officecli'].get('sha256'):
        raise OfficeError('OfficeCLI binary changed. Revalidate/reinstall; not running an unverified update.')
    return p


def office_command(d, args, timeout=180):
    allowed={'--version','--help','help','create','view','get','query','validate','set','add','remove',
             'move','swap','copy','copyfrom','batch','dump','merge','save','close','raw','raw-get','raw-set','load_skill'}
    if not args or args[0] not in allowed:
        raise OfficeError('Unsupported adapter command. install/update/skills/watch/config are intentionally not executed.')
    # Absolute input paths in helper-generated commands. User passthrough remains a tool, not a filesystem sandbox.
    return run([str(office_binary(d)),*args],env=office_env(),timeout=timeout)


def page_indices(spec,total,limit=200):
    if not 0<total<=100000:raise OfficeError('Invalid page count')
    if not spec or spec=='all': result=list(range(total))
    else:
        result=[]
        for item in spec.split(','):
            if re.fullmatch(r'[1-9]\d*',item): result.append(int(item)-1)
            elif re.fullmatch(r'[1-9]\d*-[1-9]\d*',item):
                start,end=map(int,item.split('-'))
                if end<start or end-start>limit:raise OfficeError('Invalid/oversized page range')
                result.extend(range(start-1,end))
            else:raise OfficeError('Pages must be 1-based, e.g. 1,3-5 or all')
        if len(set(result))!=len(result):raise OfficeError('Duplicate page numbers')
    if len(result)>limit:raise OfficeError(f'More than {limit} pages; request explicit smaller ranges')
    if not result or min(result)<0 or max(result)>=total:raise OfficeError('Page range is out of bounds')
    return result


def prepare(src,out):
    src=source_file(src);out=absolute(out)
    if src.suffix.lower()!=out.suffix.lower():raise OfficeError('Working copy must have the same file type')
    f=facts(src)
    receipt=out.with_name(out.name+'.origin.json')
    no_symlinks(out);no_symlinks(receipt)
    if out.exists() or receipt.exists():raise OfficeError('Working copy/receipt already exists')
    new_file(out,src.read_bytes())
    try:new_file(receipt,json_bytes({'schema':1,'source':f,'working_copy':str(out)}))
    except BaseException:
        out.unlink();raise
    return {'copy':str(out),'receipt':str(receipt),'original_unchanged':file_sha(src)==f['sha256']}


def extract(src,out,pages=None):
    src=source_file(src);info=facts(src);assert_render_safe(info)
    if src.suffix.lower()=='.pdf':
        import pdfplumber
        sections=[]
        with pdfplumber.open(src) as pdf:
            for idx in page_indices(pages,len(pdf.pages)):
                text=pdf.pages[idx].extract_text() or ''
                sections.append(f'## Page {idx+1}\n\n{text or "[No extractable text. Inspect the rendered page; do not assume it is blank.]"}')
        content='\n\n'.join(sections)+'\n'
    else:
        if pages:raise OfficeError('--pages applies to PDF text extraction only')
        from markitdown import MarkItDown
        converter=MarkItDown(enable_plugins=False)
        # Stream path avoids interpreting a caller-supplied URL. No LLM/cloud/third-party plugins configured.
        with src.open('rb') as f:
            result=converter.convert_stream(f,file_extension=src.suffix.lower())
        content=result.text_content
    new_file(absolute(out),content.encode('utf-8'))
    return {'output':str(absolute(out)),'source_sha256':info['sha256'],
            'coverage':'text extraction only; figures/layout must be inspected visually',
            'ocr':False,'cloud_conversion':False}


def pdf_tables(src,out,pages):
    import pdfplumber
    p=source_file(src)
    if p.suffix.lower()!='.pdf':raise OfficeError('PDF required')
    facts(p)
    with pdfplumber.open(p) as pdf:
        result=[{'page':i+1,'tables':pdf.pages[i].extract_tables()} for i in page_indices(pages,len(pdf.pages))]
    new_file(absolute(out),json_bytes({'source':str(p),'pages':result,'note':'Detected tables require visual cross-check.'}))
    return {'output':str(absolute(out))}


def render_pdf(pdf,out,pages,dpi):
    import pypdfium2 as pdfium
    if not 72<=dpi<=300:raise OfficeError('DPI must be 72..300')
    document=pdfium.PdfDocument(str(pdf))
    rendered=[]
    try:
        indices=page_indices(pages,len(document),limit=100)
        for idx in indices:
            page=document[idx]
            try:
                w,h=page.get_size();scale=dpi/72
                if w*h*scale*scale>30_000_000:raise OfficeError('Rendered page exceeds 30M pixels; reduce DPI')
                bitmap=page.render(scale=scale)
                try:
                    image=bitmap.to_pil()
                    target=out/f'page-{idx+1:04d}.png'
                    image.save(target)
                    target.chmod(0o600)
                    rendered.append({'page':idx+1,'file':target.name,'sha256':file_sha(target),'width':image.width,'height':image.height})
                finally:bitmap.close()
            finally:page.close()
        return {'total_pages':len(document),'complete':len(indices)==len(document),'images':rendered}
    finally:document.close()


def _render_job(src,out,pages,dpi,engine):
    info=facts(src);assert_render_safe(info)
    d=config() if engine=='officecli' else None
    if src.suffix.lower()=='.pdf':
        result=render_pdf(src,out,pages,dpi);renderer='PDFium'
    elif engine in ('auto','libreoffice'):
        lo=shutil.which('soffice') or shutil.which('libreoffice')
        if not lo:
            raise OfficeError('LibreOffice required for full Office pagination. Run office-workbench system-deps. OfficeCLI page screenshots are an explicit fallback.')
        with tempfile.TemporaryDirectory(prefix='office-render-') as td:
            temp=Path(td);profile=temp/'profile';profile.mkdir()
            # Disable macros at the highest level in a separate profile. No original Office save-back.
            (profile/'user').mkdir()
            (profile/'user/registrymodifications.xcu').write_text('''<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item></oor:items>''', encoding="utf-8", newline="\n")
            copy=temp/('input'+src.suffix);shutil.copyfile(src,copy)
            export=temp/'export';export.mkdir()
            run([lo,'-env:UserInstallation='+profile.as_uri(),'--headless','--nologo','--nodefault',
                 '--norestore','--convert-to','pdf','--outdir',str(export),str(copy)],timeout=150,
                 env={**{k:v for k,v in os.environ.items() if k not in ('DISPLAY','WAYLAND_DISPLAY')},'HOME':str(temp),'SAL_USE_VCLPLUGIN':'svp'})
            generated=export/'input.pdf'
            if not generated.is_file() or not generated.stat().st_size:raise OfficeError('LibreOffice produced no PDF')
            result=render_pdf(generated,out,pages,dpi)
            shutil.copyfile(generated,out/'preview.pdf')
            (out/'preview.pdf').chmod(0o600)
        renderer='LibreOffice + PDFium'
    else:
        if not pages or pages=='all':
            raise OfficeError('OfficeCLI screenshot fallback requires explicit pages; total DOCX page coverage is not inferred.')
        # The CLI identifies page numbers, but browser availability must be confirmed at runtime.
        max_page=info.get('slides') or 100000
        indices=page_indices(pages,max_page,limit=100)
        rendered=[]
        for idx in indices:
            target=out/f'page-{idx+1:04d}.png'
            office_command(d,['view',str(src),'screenshot','--page',str(idx+1),'-o',str(target)],timeout=120)
            if not target.is_file() or not target.stat().st_size:raise OfficeError('OfficeCLI did not produce the requested PNG')
            rendered.append({'page':idx+1,'file':target.name,'sha256':file_sha(target)})
        result={'total_pages':info.get('slides'),'complete':bool(info.get('slides') and len(indices)==info['slides']), 'images':rendered}
        renderer='OfficeCLI HTML screenshot (not Microsoft Office)'
    if file_sha(src)!=info['sha256']:raise OfficeError('Source changed during rendering; output cannot be treated as current')
    result.update({'schema':1,'source':str(src),'source_sha256':info['sha256'],
                   'renderer':renderer,'visual_review':'NOT_PERFORMED','warnings':info.get('warnings',[])})
    new_file(out/'render.json',json_bytes(result))
    return result


def render(src,out,pages,dpi,engine,worker=False):
    src=source_file(src);out=absolute(out);no_symlinks(out)
    if worker:return _render_job(src,out,pages,dpi,engine)
    if out.exists():raise OfficeError('Choose a new render directory; existing files are not overwritten')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.office-render-',dir=out.parent) as td:
        stage=Path(td)/'output';stage.mkdir()
        argv=[sys.executable,str(ROOT/'office.py'),'_render-worker',str(src),'--out-dir',str(stage),
              '--dpi',str(dpi),'--engine',engine]
        if pages:argv+=['--pages',pages]
        run(argv,timeout=240,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        # Reserve target exclusively. Publish files only after the worker completed successfully.
        out.mkdir(mode=0o700)
        for f in stage.iterdir():shutil.move(str(f),out/f.name)
    return load_json(out/'render.json')


def compare(src,dst,require_media=False,allowed_parts=None):
    a=facts(src);b=facts(dst)
    if a['format']!=b['format']:raise OfficeError('Compare requires the same format')
    result={'before_sha256':a['sha256'],'after_sha256':b['sha256'],'visual_review':'NOT_PERFORMED',
            'scope_verified':False,'issues':[]}
    if 'parts' in a:
        names=set(a['parts'])|set(b['parts'])
        changed=sorted(n for n in names if a['parts'].get(n)!=b['parts'].get(n))
        media_ok=collections.Counter(a['media'].values())==collections.Counter(b['media'].values())
        result.update(changed_parts=changed,media_bytes_preserved=media_ok)
        if require_media and not media_ok:result['issues'].append('MEDIA_CHANGED')
        if allowed_parts is not None:
            outside=[n for n in changed if n not in allowed_parts]
            result['outside_allowed_parts']=outside
            result['scope_verified']=not outside
            if outside:result['issues'].append('UNEXPECTED_PART_CHANGE')
        if a.get('slides')!=b.get('slides'):result['issues'].append('SLIDE_COUNT_CHANGED')
        result['limitations']='Media bytes do not verify cropping, position, drawing shapes, fonts, or layout. Review renders.'
    else:
        result.update(before_pages=a['pages'],after_pages=b['pages'])
        if a['pages']!=b['pages']:result['issues'].append('PAGE_COUNT_CHANGED')
        if require_media:raise OfficeError('--require-media-preserved is for DOCX/PPTX only')
    return result


def pdf_edit(operation,inputs,out,pages=None,angle=90):
    from pypdf import PdfReader,PdfWriter
    files=[source_file(x) for x in inputs]
    if any(x.suffix.lower()!='.pdf' for x in files):raise OfficeError('PDF files required')
    target=absolute(out);no_symlinks(target)
    if target.exists():raise OfficeError('Output exists; never edit the original in place')
    if target.suffix.lower()!='.pdf':raise OfficeError('Output must end in .pdf')
    import io
    writer=PdfWriter()
    for src in files:
        reader=PdfReader(src)
        if reader.is_encrypted:raise OfficeError('Encrypted PDF is not supported here')
        indices=page_indices(pages if operation!='merge' else None,len(reader.pages))
        if operation=='rotate':
            selected=set(indices)
            for i,page in enumerate(reader.pages):
                writer.add_page(page)
                if i in selected:writer.pages[-1].rotate(angle)
        else:
            for i in indices:writer.add_page(reader.pages[i])
    stream=io.BytesIO();writer.write(stream);writer.close()
    # Reopen generated bytes before publishing.
    count=len(PdfReader(io.BytesIO(stream.getvalue())).pages)
    new_file(target,stream.getvalue())
    return {'output':str(target),'pages':count,'visual_review':'NOT_PERFORMED',
            'warning':'Page-level rebuild; not a signature/form/bookmark preserving workflow. No arbitrary PDF text replacement.'}


def doctor(p=None, strict=False):
    p=p or paths();d=load_json(p['config']) if p['config'].is_file() else {}
    modules=['markitdown','pypdf','pdfplumber','pypdfium2','python-docx','python-pptx','Pillow','defusedxml']
    versions={}
    # Installer invokes doctor with bootstrap interpreter; probe the installed interpreter separately.
    python=d.get('python')
    if python and Path(python).is_file() and absolute(python)!=absolute(sys.executable):
        probe=run([python,'-c',"import importlib.metadata as m,json; names="+repr(modules)+"; out={};\nfor n in names:\n try: out[n]=m.version(n)\n except m.PackageNotFoundError: out[n]=None\nprint(json.dumps(out))"],check=False)
        if probe.returncode==0:
            with contextlib.suppress(ValueError):versions=json.loads(probe.stdout)
    else:
        for name in modules:
            try:versions[name]=importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:versions[name]=None
    office='MISSING'
    if d.get('officecli',{}).get('path'):
        try:
            b=office_binary(d);r=run([str(b),'--version'],timeout=30,env=office_env())
            office=r.stdout.strip() or 'AVAILABLE'
        except (OfficeError,OSError) as e:office='ERROR: '+str(e)
    lo=shutil.which('soffice') or shutil.which('libreoffice')
    font_info='UNKNOWN (fontconfig unavailable)'
    if shutil.which('fc-list'):
        fr=run(['fc-list',':lang=ja','family'],timeout=20,check=False)
        font_info='AVAILABLE' if fr.returncode==0 and fr.stdout.strip() else 'MISSING'
    incomplete=not d or d.get('features',{}).get('assets_only') or any(not versions.get(x) for x in modules) or office.startswith(('MISSING','ERROR'))
    capabilities={'document_tools':'NOT_READY' if incomplete else 'AVAILABLE',
                  'office_full_page_render':'AVAILABLE' if lo and versions.get('pypdfium2') else 'NOT_READY',
                  'japanese_fonts':font_info,'real_officecli_edit_smoke':'NOT_RUN_BY_DOCTOR',
                  'visual_quality':'NOT_VERIFIED','mcp':'OPT_IN_ONLY'}
    print(json.dumps({'version':d.get('kit_version'),'paths':{k:str(v) for k,v in p.items()},
                      'officecli':office,'python_packages':versions,'libreoffice':lo,
                      'capabilities':capabilities},ensure_ascii=False,indent=2))
    return 2 if strict and (incomplete or not lo or font_info!='AVAILABLE') else 0


def codex_mcp(enable, apply=False):
    p=paths();d=config();no_symlinks(p['codex'])
    f=p['codex']/'config.toml';no_symlinks(f)
    before=f.read_bytes() if f.exists() else b''
    try:parsed=tomllib.loads(before.decode())
    except (ValueError,UnicodeError) as e:raise OfficeError('Invalid Codex TOML; no change made') from e
    entry=parsed.get('mcp_servers',{}).get(MCP_NAME)
    desired={'command':str(p['launcher']),'args':['mcp']}
    if entry:
        if entry.get('command')!=desired['command'] or entry.get('args',[])!=desired['args']:
            raise OfficeError('Same-name MCP belongs to another configuration; not replacing it')
        extras=set(entry)-{'command','args','enabled','startup_timeout_sec','tool_timeout_sec'}
        if extras:raise OfficeError('MCP entry has custom settings; manage it manually')
    if enable:
        office_binary(d)
        if entry:return {'status':'SKIP','name':MCP_NAME}
        argv=['codex','mcp','add',MCP_NAME,'--',str(p['launcher']),'mcp']
    else:
        if not entry:return {'status':'SKIP','name':MCP_NAME}
        argv=['codex','mcp','remove',MCP_NAME]
    if not apply:return {'command':argv,'apply':False,'warning':'Native MCP has editing access under the user account. Not a sandbox.'}
    if not shutil.which('codex'):raise OfficeError('Codex CLI is not available')
    with lock(p['data']/'.mcp.lock'):
        if (f.read_bytes() if f.exists() else b'')!=before:raise OfficeError('Codex config changed; retry after reviewing it')
        if before:atomic_write(p['data']/('backups/config-before-mcp-'+time.strftime('%Y%m%dT%H%M%S')+'-'+str(time.time_ns())+'.toml'),before)
        result=run(argv,timeout=60,env={**os.environ,'CODEX_HOME':str(p['codex'])},cwd=str(p['home']),check=False)
        after=tomllib.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        # Do not revert blindly: another app may have updated config concurrently.
        def without_ours(v):
            v=json.loads(json.dumps(v));s=v.get('mcp_servers',{});s.pop(MCP_NAME,None)
            if not s:v.pop('mcp_servers',None)
            return v
        if without_ours(before_parsed:=parsed)!=without_ours(after):
            raise OfficeError('Other Codex settings changed during registration. Backup retained; inspect before proceeding.')
        got=after.get('mcp_servers',{}).get(MCP_NAME)
        if result.returncode or (enable and (not got or got.get('command')!=desired['command'] or got.get('args')!=['mcp'])) or (not enable and got):
            raise OfficeError('MCP command failed/read-back differs. Core install is intact; inspect /mcp and config backup.')
    return {'name':MCP_NAME,'status':'ENABLED' if enable else 'DISABLED'}


def visual_status(directory):
    directory=absolute(directory);r=load_json(directory/'render.json')
    source=source_file(r['source'])
    if file_sha(source)!=r['source_sha256']:raise OfficeError('Render is stale: source changed')
    for item in r['images']:
        name=item['file']
        if Path(name).name!=name:raise OfficeError('Unsafe render file')
        p=directory/name;no_symlinks(p)
        if not p.is_file() or file_sha(p)!=item['sha256']:raise OfficeError('Render image missing or changed')
    return {'source_hash_current':True,'image_hashes_current':True,'all_pages_rendered':r.get('complete'),
            'visual_review':'NOT_VERIFIED_BY_CODE','note':'Open every relevant PNG. Hash checks do not detect layout defects.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',action='version',version='Office Workbench '+load_json(ROOT/'versions.json')['kit_version'])
    sub=parser.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('doctor');q.add_argument('--strict',action='store_true')
    sub.add_parser('paths');sub.add_parser('system-deps')
    q=sub.add_parser('officecli');q.add_argument('args',nargs=argparse.REMAINDER)
    q=sub.add_parser('python');q.add_argument('args',nargs=argparse.REMAINDER,help='run a trusted script with the private Python; not a sandbox')
    q=sub.add_parser('inspect');q.add_argument('file');q.add_argument('--output')
    q=sub.add_parser('prepare');q.add_argument('file');q.add_argument('--output',required=True)
    q=sub.add_parser('verify-copy');q.add_argument('file')
    q=sub.add_parser('extract');q.add_argument('file');q.add_argument('--output',required=True);q.add_argument('--pages')
    q=sub.add_parser('pdf-tables');q.add_argument('file');q.add_argument('--output',required=True);q.add_argument('--pages')
    for name in ('render','_render-worker'):
        q=sub.add_parser(name);q.add_argument('file');q.add_argument('--out-dir',required=True);q.add_argument('--pages');q.add_argument('--dpi',type=int,default=144);q.add_argument('--engine',choices=['auto','libreoffice','officecli'],default='auto')
    q=sub.add_parser('preview');q.add_argument('file');q.add_argument('--output',required=True)
    q=sub.add_parser('compare');q.add_argument('before');q.add_argument('after');q.add_argument('--output');q.add_argument('--require-media-preserved',action='store_true');q.add_argument('--allowed-part',action='append')
    q=sub.add_parser('verify-renders');q.add_argument('directory')
    for name in ('pdf-select','pdf-rotate','pdf-merge'):
        q=sub.add_parser(name);q.add_argument('inputs',nargs='+' if name=='pdf-merge' else 1);q.add_argument('--output',required=True)
        if name!='pdf-merge':q.add_argument('--pages',required=True)
        if name=='pdf-rotate':q.add_argument('--angle',type=int,choices=[90,180,270],default=90)
    for name in ('mcp-enable','mcp-disable'):
        q=sub.add_parser(name);q.add_argument('--apply',action='store_true')
    sub.add_parser('mcp')
    q=sub.add_parser('docling');q.add_argument('args',nargs=argparse.REMAINDER)
    q=sub.add_parser('smoke-test');q.add_argument('--out-dir',required=True)
    args=parser.parse_args()
    if args.cmd=='doctor':return doctor(strict=args.strict)
    if args.cmd=='paths':r={k:str(v) for k,v in paths().items()}
    elif args.cmd=='system-deps':
        from install import system_packages
        r=system_packages(False)
    elif args.cmd=='officecli':
        tail=args.args[1:] if args.args[:1]==['--'] else args.args
        res=office_command(config(),tail);print(res.stdout,end='');return 0
    elif args.cmd=='python':
        tail=args.args[1:] if args.args[:1]==['--'] else args.args
        if not tail:raise OfficeError('Pass a trusted script or Python arguments')
        d=config();os.execv(d['python'],[d['python'],*tail])
    elif args.cmd=='inspect':
        r=facts(args.file)
        if args.output:new_file(absolute(args.output),json_bytes(r))
    elif args.cmd=='prepare':r=prepare(args.file,args.output)
    elif args.cmd=='verify-copy':
        target=source_file(args.file);receipt=load_json(target.with_name(target.name+'.origin.json'))
        original=source_file(receipt['source']['path'])
        if file_sha(original)!=receipt['source']['sha256']:raise OfficeError('ORIGINAL_CHANGED: source differs from preparation receipt')
        if receipt.get('working_copy')!=str(target):raise OfficeError('Working copy path differs from receipt')
        r={'original_unchanged':True,'working_copy':str(target),'visual_review':'NOT_VERIFIED'}
    elif args.cmd=='extract':r=extract(args.file,args.output,args.pages)
    elif args.cmd=='pdf-tables':r=pdf_tables(args.file,args.output,args.pages)
    elif args.cmd in ('render','_render-worker'):r=render(args.file,args.out_dir,args.pages,args.dpi,args.engine,args.cmd=='_render-worker')
    elif args.cmd=='preview':
        src=source_file(args.file);info=facts(src);assert_render_safe(info);dest=absolute(args.output)
        if dest.suffix.lower()!='.html':raise OfficeError('Preview output must be .html')
        if dest.exists():raise OfficeError('Output exists')
        with tempfile.TemporaryDirectory() as td:
            temp=Path(td)/'preview.html'
            office_command(config(),['view',str(src),'html','-o',str(temp)])
            if not temp.is_file():raise OfficeError('No HTML produced')
            new_file(dest,temp.read_bytes())
        r={'output':str(dest),'warning':'OfficeCLI preview; not Microsoft Office. External JS/CDN resources may be required. PNG verification is separate.'}
    elif args.cmd=='compare':
        r=compare(args.before,args.after,args.require_media_preserved,args.allowed_part)
        if args.output:new_file(absolute(args.output),json_bytes(r))
        print(json.dumps(r,ensure_ascii=False,indent=2));return 2 if r['issues'] else 0
    elif args.cmd=='verify-renders':r=visual_status(args.directory)
    elif args.cmd.startswith('pdf-'):
        r=pdf_edit(args.cmd[4:],args.inputs,args.output,getattr(args,'pages',None),getattr(args,'angle',90))
    elif args.cmd in ('mcp-enable','mcp-disable'):r=codex_mcp(args.cmd=='mcp-enable',args.apply)
    elif args.cmd=='mcp':
        binary=office_binary(config());os.execve(str(binary),[str(binary),'mcp'],office_env())
    elif args.cmd=='docling':
        d=config();binary=Path(d['release'])/'docling-venv/bin/docling'
        if not binary.is_file():raise OfficeError('Install with --with-docling first (large optional environment)')
        tail=args.args[1:] if args.args[:1]==['--'] else args.args
        if not tail:tail=['--help']
        # CLI is local. OCR is an explicit later decision. Model assets may download on first conversion.
        os.execve(str(binary),[str(binary),*tail],{**os.environ,'DOCLING_MCP_CONVERSION_MODE':'local'})
    elif args.cmd=='smoke-test':
        from tests.smoke_local import smoke
        r=smoke(absolute(args.out_dir),config())
        print(json.dumps(r,ensure_ascii=False,indent=2))
        return 2 if r['summary']=='FAIL' else (3 if r['summary']=='PARTIAL' else 0)
    else:raise OfficeError('Unknown command')
    print(json.dumps(r,ensure_ascii=False,indent=2));return 0


from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':
    try:sys.exit(main())
    except (OfficeError,OSError,ValueError,zipfile.BadZipFile,ET.ParseError,ImportError) as e:
        print('ERROR: '+str(e),file=sys.stderr);sys.exit(2)
