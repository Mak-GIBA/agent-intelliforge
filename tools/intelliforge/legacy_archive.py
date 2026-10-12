"""Small source builder retaining the original archive layout and bootstrap."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile


def build(directory):
    layout = json.loads((directory/'payload-layout.json').read_text(encoding='utf-8'))
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=layout['compression']) as output:
        for record in layout['entries']:
            info=zipfile.ZipInfo(record['filename'],tuple(record['date_time']))
            for key,value in record.items():
                if key not in ('filename','date_time'):setattr(info,key,value)
            output.writestr(info,(directory/record['filename']).read_bytes())
    raw=archive.getvalue();encoded=base64.b64encode(raw).decode()
    template=(directory/'bootstrap.sh.in').read_text(encoding='utf-8')
    width=layout['line_width']
    return template.replace('@PAYLOAD_SHA256@',hashlib.sha256(raw).hexdigest()).replace('@PAYLOAD_BASE64@','\n'.join(encoded[index:index+width] for index in range(0,len(encoded),width)))


def main(directory):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    name=json.loads((directory/'EXTRACTED.json').read_text(encoding='utf-8'))['source_installer']
    target=directory.parents[1]/name;expected=build(directory)
    if args.check:
        if target.read_text(encoding='utf-8')!=expected:parser.exit(1,'Standalone differs from canonical source: '+name+'\n')
    else:target.write_text(expected,encoding='utf-8',newline='\n')
    print(('Checked ' if args.check else 'Built ')+name)
