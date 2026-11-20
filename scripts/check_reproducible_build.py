#!/usr/bin/env python3
"""Build twice from committed CSV inputs and compare every generated artifact."""
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def build_and_hash():
    for script in ('import_csv.py','build.py'):
        subprocess.run([sys.executable,str(ROOT/'scripts'/script)],cwd=ROOT,check=True)
    files=[ROOT/'data/catalog.json',ROOT/'index.html',ROOT/'coverage.json',ROOT/'provenance.json',
           *(ROOT/'dist').rglob('*')]
    return {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files if path.is_file()}


if __name__=='__main__':
    first=build_and_hash();second=build_and_hash()
    changed=sorted(path for path in first.keys()|second.keys() if first.get(path)!=second.get(path))
    if changed:raise SystemExit('Non-reproducible build: '+', '.join(changed))
    print(f'PASS: {len(first)} generated artifacts reproduced byte for byte')
