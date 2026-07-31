#!/usr/bin/env python3
"""Pick the first live Claude provider from the shared file, then configure worker."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import httpx

paths = [Path('/mnt/sdcard/ARMY/providers/claude.providers'), Path('/sdcard/ARMY/providers/claude.providers')]
provider_file = next((p for p in paths if p.exists()), paths[-1])
settings = Path('/home/worker/.claude/settings.json')
entries=[]
for raw in provider_file.read_text(encoding='utf-8').splitlines():
    line=raw.strip()
    if not line or line.startswith('#'): continue
    parts=[x.strip() for x in line.split('|')]
    if len(parts) not in (3,4) or not all(parts): continue
    key,url,name=parts[:3]
    model=parts[3] if len(parts)==4 else 'claude-sonnet-5'
    entries.append((key,url.rstrip('/'),name,model))

if not entries:
    print('No valid providers in claude.providers', file=sys.stderr); raise SystemExit(1)

selected=None
for key,url,name,model in entries:
    try:
        response=httpx.post(f'{url}/v1/messages', headers={'authorization':f'Bearer {key}','anthropic-version':'2023-06-01','content-type':'application/json'}, json={'model':model,'max_tokens':1,'messages':[{'role':'user','content':'OK'}]}, timeout=25)
        if response.status_code < 400:
            selected=(key,url,name,model); break
        print(f'SKIP {name}: HTTP {response.status_code}')
    except httpx.HTTPError as exc:
        print(f'SKIP {name}: {type(exc).__name__}')

if not selected:
    print('No live Claude provider found', file=sys.stderr); raise SystemExit(1)
key,url,name,model=selected
settings.parent.mkdir(parents=True, exist_ok=True)
data=json.loads(settings.read_text()) if settings.exists() else {}
data['model']=model
data['env']={'ANTHROPIC_BASE_URL':url,'ANTHROPIC_AUTH_TOKEN':key}
settings.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
settings.chmod(0o600)
print(f'SELECTED {name} -> {model}')
