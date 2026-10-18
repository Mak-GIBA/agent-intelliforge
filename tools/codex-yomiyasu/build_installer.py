#!/usr/bin/env python3
"""Build/check the standalone installer deterministically from reviewed source assets."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import zlib

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parents[1]/'install_codex_yomiyasu.sh'



def build() -> str:
    assets = {}
    for prefix, folder in [('', ROOT/'assets'), ('tests/', ROOT/'tests'), ('evals/', ROOT/'evals')]:
        for p in sorted(folder.rglob('*')):
            if p.is_symlink():
                raise ValueError('Symlink in source assets: '+str(p))
            if p.is_file() and '__pycache__' not in p.parts:
                assets[prefix+p.relative_to(folder).as_posix()] = p.read_text(encoding='utf-8')
    raw = zlib.compress(json.dumps(assets, ensure_ascii=False, sort_keys=True,
                                  separators=(',', ':')).encode(), 9)
    source = (ROOT/'installer.py').read_text(encoding='utf-8')
    source = source.replace("ASSET_B64 = '@ASSET_B64@'", 'ASSET_B64 = '+repr(base64.b64encode(raw).decode()))
    source = re.sub(r"^ASSET_SHA256 = '.*'$", 'ASSET_SHA256 = '+repr(hashlib.sha256(raw).hexdigest()), source, flags=re.M)
    source = source.replace("if __name__ == '__main__':\n    raise SystemExit(main())",
                            "if __name__ == '__main__':\n    SELF_SCRIPT = abs_path(sys.argv[1])\n    raise SystemExit(main(sys.argv[2:]))")
    compile(source, 'embedded-installer.py', 'exec')
    return shell_header()+source.rstrip()+'\n\nYOMI_INSTALL_PY\n'


def shell_header():
    versions=json.loads((ROOT/'assets/scripts/runtime-versions.json').read_text(encoding='utf-8'))
    cases=[]
    for key,label in [('linux-x64','Linux-x86_64'),('linux-arm64','Linux-aarch64'),('darwin-x64','Darwin-x86_64'),('darwin-arm64','Darwin-arm64')]:
        spec=versions['platforms'][key]['uv']
        cases.append(f"      {label}) url='{spec['url']}';digest='{spec['sha256']}';;")
    return (ROOT/'bootstrap/python.sh.in').read_text(encoding='utf-8').replace('@UV_CASES@','\n'.join(cases)).replace('@PYTHON_VERSION@',versions['python'])


def powershell(shell):
    source=shell.split("<<'YOMI_INSTALL_PY'\n",1)[1].rsplit('\nYOMI_INSTALL_PY',1)[0]
    versions=json.loads((ROOT/'assets/scripts/runtime-versions.json').read_text(encoding='utf-8'))
    cases=[]
    for key,label in [('win32-x64','X64'),('win32-arm64','Arm64')]:
        spec=versions['platforms'][key]['uv']
        cases.append(f"                '{label}' {{ $url='{spec['url']}'; $digest='{spec['sha256']}' }}")
    return (ROOT/'bootstrap/python.ps1.in').read_text(encoding='utf-8').replace('@UV_PS_CASES@','\n'.join(cases)).replace('@PYTHON_VERSION@',versions['python']).replace('@PYTHON_PAYLOAD@',base64.b64encode(source.encode('utf-8')).decode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    generated = build()
    outputs={OUTPUT:generated,OUTPUT.with_name('install_kotonoha.sh'):generated,
             OUTPUT.with_name('install_kotonoha.ps1'):powershell(generated)}
    for path,text in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != text:
                parser.exit(1,'Generated installer differs: '+str(path)+'\n')
            print('Installer matches maintained source: '+path.name)
        else:
            path.write_text(text,encoding='utf-8');print('Built '+str(path))


if __name__ == '__main__':
    main()
