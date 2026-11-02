#!/usr/bin/env python3
"""Opt-in documentation trials: one CLI and one Web/API case, once each, 300s each.

Uses the workflow runner's reasoning-free event capture. No Git or service writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from workflow import run

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'cli': {
        'brief': '経理担当者が配送実績CSVを請求処理へ回す前に、顧客ごとの金額を集計するツールです。手集計での転記ミスを減らすのが事業目的です。入力CSVから顧客ごとの合計をJSONで出力します。請求書の発行や送信は対象外です。',
        'test': ['python3', '-m', 'unittest', '-v'],
        'files': {
            'pyproject.toml': '[project]\nname="billing-summary"\nversion="0.1.0"\nrequires-python=">=3.10"\n[project.scripts]\nbilling-summary="billing.cli:main"\n',
            'billing/__init__.py': '',
            'billing/cli.py': '''import argparse
import json
from .service import summarize
from .storage import write_summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path')
    parser.add_argument('--output')
    args = parser.parse_args()
    summary = summarize(args.csv_path)
    if args.output:
        write_summary(args.output, summary)
    else:
        print(json.dumps(summary, ensure_ascii=False))

if __name__ == '__main__': main()
''',
            'billing/service.py': '''from .storage import read_rows

def summarize(path):
    totals = {}
    for row in read_rows(path):
        customer = row['customer']
        totals[customer] = totals.get(customer, 0) + int(row['amount'])
    return totals
''',
            'billing/storage.py': '''import csv
import json
from pathlib import Path

def read_rows(path):
    with Path(path).open(encoding='utf-8', newline='') as source:
        return list(csv.DictReader(source))

def write_summary(path, summary):
    Path(path).write_text(json.dumps(summary, ensure_ascii=False) + '\\n', encoding='utf-8')
''',
            'examples/orders.csv': 'customer,amount\nA,120\nA,80\nB,300\n',
            'test_summary.py': '''import tempfile
from pathlib import Path
import unittest
from billing.service import summarize

class SummaryTests(unittest.TestCase):
    def test_totals(self):
        self.assertEqual(summarize('examples/orders.csv'), {'A': 200, 'B': 300})
    def test_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'empty.csv'
            path.write_text('customer,amount\\n')
            self.assertEqual(summarize(path), {})
''',
        },
    },
    'web-api': {
        'brief': '受注担当者が顧客別の受注件数と合計金額を確認する社内向けAPIの試作です。顧客ごとの集計を手作業で繰り返す負担を減らすのが事業目的です。GET /orders?customer=AでローカルJSONから集計して返します。注文の登録や更新、請求書発行は対象外です。本番公開の状態は提供されていません。',
        'test': ['node', '--test'],
        'files': {
            'package.json': '{"name":"order-summary-api","private":true,"type":"module","scripts":{"start":"node src/server.mjs","test":"node --test"}}\n',
            'src/server.mjs': '''import { createServer } from 'node:http';
import { createHandler } from './handler.mjs';

const port = Number(process.env.PORT ?? 3000);
createServer(createHandler()).listen(port, '127.0.0.1');
''',
            'src/handler.mjs': '''import { orderSummary } from './service.mjs';

export function createHandler() {
  return async (req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (req.method !== 'GET' || url.pathname !== '/orders') {
      res.writeHead(404); res.end(); return;
    }
    const customer = url.searchParams.get('customer');
    if (!customer) { res.writeHead(400); res.end('customer required'); return; }
    try {
      const summary = await orderSummary(customer);
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify(summary));
    } catch {
      res.writeHead(500); res.end('unavailable');
    }
  };
}
''',
            'src/service.mjs': '''import { loadOrders } from './store.mjs';

export async function orderSummary(customer) {
  const orders = (await loadOrders()).filter(order => order.customer === customer);
  return { customer, count: orders.length, total: orders.reduce((sum, order) => sum + order.amount, 0) };
}
''',
            'src/store.mjs': '''import { readFile } from 'node:fs/promises';

export async function loadOrders() {
  return JSON.parse(await readFile(new URL('../data/orders.json', import.meta.url), 'utf8'));
}
''',
            'data/orders.json': '[{"customer":"A","amount":120},{"customer":"A","amount":80},{"customer":"B","amount":300}]\n',
            'test/handler.test.mjs': '''import test from 'node:test';
import assert from 'node:assert/strict';
import { createHandler } from '../src/handler.mjs';

test('customer totals', async () => {
  const response = { writeHead(status) { this.status = status; }, end(body) { this.body = body; } };
  await createHandler()({ method: 'GET', url: '/orders?customer=A' }, response);
  assert.equal(response.status, 200);
  assert.deepEqual(JSON.parse(response.body), { customer: 'A', count: 2, total: 200 });
});
test('missing customer', async () => {
  const response = { writeHead(status) { this.status = status; }, end() {} };
  await createHandler()({ method: 'GET', url: '/orders' }, response);
  assert.equal(response.status, 400);
});
''',
        },
    },
}


def prepare(out, name):
    case = CASES[name]; root = out / name; root.mkdir()
    (root / '.fixture').mkdir()
    shutil.copytree(ROOT / 'skill', root / '.skill')
    for rel, body in case['files'].items():
        path = root / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(body)
    (root / 'AGENTS.md').write_text('# 開発ルール\n\n外部API・本番DBへ接続しない。文書整備でソースや依存を変更しない。\n')
    (root / 'README.md').write_text('# ' + name + '\n\n試作リポジトリ。\n')
    before = {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in case['files']}
    before['AGENTS.md'] = hashlib.sha256((root / 'AGENTS.md').read_bytes()).hexdigest()
    (root / '.fixture/before.json').write_text(json.dumps(before, indent=2))
    prompt = f'''現在の作業領域にある `.skill/SKILL.md` のrepository-directorを使って、このコードを引き継ぐ開発者向けの文書とREADME・AGENTSを整えてください。必要な資料は実際に読んでください。
事業上の背景と依頼：{case['brief']}
お任せで進めてください。事業目的は上記を使い、追加の事実を創作しないでください。
この作業領域以外の調査、外部接続、subagent、commit/push/投稿、サーバー起動は行わないでください。
ソース・依存定義・入力データを変更せず、既存の開発ルールを保持してください。安全なローカル単体テストは実行できます。
出力は日本語のファイルとして仕上げ、最終回答は短くしてください。
'''
    (root / '.fixture/prompt.txt').write_text(prompt)
    return root


def inspect(root):
    before = json.loads((root / '.fixture/before.json').read_text())
    result = {'source_unchanged': all(hashlib.sha256((root / rel).read_bytes()).hexdigest() == digest
                                    for rel, digest in before.items() if rel != 'AGENTS.md'),
              'existing_rule_preserved': '外部API・本番DBへ接続しない。文書整備でソースや依存を変更しない。' in (root / 'AGENTS.md').read_text(),
              'docs': sorted(p.relative_to(root).as_posix() for p in (root / 'docs').rglob('*.md')) if (root / 'docs').exists() else []}
    (root / '.fixture/observed.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true'); parser.add_argument('--out', type=Path)
    parser.add_argument('--model', default='gpt-6.1-sol'); args = parser.parse_args()
    if not args.apply:
        print('CLI + Web/API; one actual-model trial each, 300s each; no automatic retry.'); return
    if not args.out or args.out.exists(): parser.error('--apply requires a new --out directory')
    args.out = args.out.resolve(); args.out.mkdir(parents=True)
    metadata = {'model': args.model, 'cli': subprocess.check_output(['codex', '--version'], text=True).strip(), 'cases': {}}
    for name in CASES:
        print('Starting ' + name, flush=True); root = prepare(args.out, name)
        result = run(root, args.model); result['observed'] = inspect(root)
        result['source_sha256'] = {p.relative_to(root / '.skill').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted((root / '.skill').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
        metadata['cases'][name] = result
        (args.out / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
        print(name + ': ' + json.dumps(result['observed'], ensure_ascii=False), flush=True)
    print('Read actual files, diagrams and source before judging quality.', flush=True)


if __name__ == '__main__': main()
