#!/usr/bin/env python3
"""
setup_3way_integration_patch.py

Single-script patcher that performs a safe, idempotent 3-way integration between:
 - Client Customization service (exact file: /home/hp/AIAutomationProjects/saas_demo/the13th/client_customization_app.py)
 - App Intelligence service (exact file: /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/app_intelligence_app.py)

What it does:
 1. Creates timestamped backups of the two target files.
 2. Inserts non-blocking relay helpers that POST events to Control Core (env var: CC_CONTROL_CORE_URL).
 3. Adds calls into existing endpoints that create events (client creation, intelligence event ingestion).
 4. Updates .env.example for both services to include CC_CONTROL_CORE_URL and CC_SYS_API_KEY defaults.

Design constraints:
 - Edits are idempotent (script will not duplicate insertions if run multiple times).
 - Uses httpx in background threads to avoid blocking request handling.
 - No removal of existing functionality.

Run (exact):
  cd /home/hp/AIAutomationProjects/saas_demo/the13th
  python setup_3way_integration_patch.py

After running, restart services (keep them in separate shells):
  # Client Customization (shell 1)
  source <path-to-venv>/bin/activate  # your project venv
  export $(grep -v '^#' client_customization/.env | xargs) || true
  python client_customization_app.py

  # App Intelligence (shell 2)
  source <path-to-venv>/bin/activate
  export $(grep -v '^#' app_intelligence/.env | xargs) || true
  python app_intelligence_app.py

Verify by posting a new client and/or event and checking Control Core metrics:
  curl -X POST http://localhost:8001/api/clients -H "X-API-KEY: dev-default-api-key" -H "Content-Type: application/json" -d '{"client_id":"agent007","name":"Bond Realty"}'
  curl -X POST http://localhost:8011/api/events -H "X-SYS-API-KEY: supersecret_sys_key" -H "Content-Type: application/json" -d '{"client_id":"agent007","action":"signup","user":"bond","metadata":{}}'
  curl -s http://localhost:8021/metrics | jq

"""
from __future__ import annotations
import shutil
from pathlib import Path
from datetime import datetime
import re

ROOT = Path('/home/hp/AIAutomationProjects/saas_demo/the13th')
CLIENT_FILE = ROOT / 'client_customization_app.py'
INTEL_FILE = ROOT / 'app_intelligence' / 'app_intelligence_app.py'

BACKUP_DIR = ROOT / 'patch_backups'
BACKUP_DIR.mkdir(exist_ok=True)

def backup(file: Path) -> Path:
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    dest = BACKUP_DIR / f"{file.name}.bak.{ts}"
    shutil.copy2(file, dest)
    return dest

INSERT_MARKER = '# === INTEGRATION: CONTROL CORE RELAY ==='

relay_helper = (
    f"\n{INSERT_MARKER}\n"
    "# helpers for relaying events to Control Core (idempotent insertion)\n"
    "import threading\n"
    "import json\n"
    "try:\n"
    "    import httpx\n"
    "except Exception:\n"
    "    httpx = None\n"
    "\n"
    "CC_CONTROL_CORE_URL = os.getenv('CC_CONTROL_CORE_URL', 'http://localhost:8021')\n"
    "CC_SYS_API_KEY = os.getenv('CC_SYS_API_KEY', 'supersecret_sys_key')\n"
    "\n"
    "def _post_to_control_core(payload: dict, timeout: int = 5) -> None:\n"
    "    \"\"\"Background post to Control Core using httpx (runs in thread).\"\"\"\n"
    "    def _worker(p):\n"
    "        try:\n"
    "            if httpx is None:\n"
    "                return\n"
    "            with httpx.Client(timeout=timeout) as client:\n"
    "                client.post(f\"{CC_CONTROL_CORE_URL}/api/events\", json=p, headers={\"X-SYS-API-KEY\": CC_SYS_API_KEY})\n"
    "        except Exception:\n"
    "            return\n"
    "    threading.Thread(target=_worker, args=(payload,), daemon=True).start()\n"
    f"{INSERT_MARKER}\n"
)


# Patch Client Customization: call relay when creating a client
def patch_client_customization():
    text = CLIENT_FILE.read_text()
    if INSERT_MARKER in text:
        print('Client customization already patched — skipping')
        return
    backup_path = backup(CLIENT_FILE)
    print('Backed up', CLIENT_FILE, '->', backup_path)
    # Insert helper after imports block (after first big import section)
    # Find position after last import statement
    imports_end = 0
    for m in re.finditer(r"^from\s+.*|^import\s+.*", text, flags=re.M):
        imports_end = m.end()
    new_text = text[:imports_end] + relay_helper + text[imports_end:]

    # Now find create_client endpoint and inject a call to _post_to_control_core
    # locate def create_client(...)
    pattern = r"def\s+create_client\s*\(.*?\):"
    m = re.search(pattern, new_text, flags=re.S)
    if not m:
        print('Could not find create_client() in', CLIENT_FILE)
        CLIENT_FILE.write_text(new_text)
        return
    # find location after function signature line
    sig_end = m.end()
    # inject after parameter validation block — we'll insert right after `require_api_key(x_api_key)` occurrences
    insert_pos = new_text.find('\n', sig_end) + 1
    # create small payload build and call
    injection = "\n    # relay: notify Control Core about new client (best-effort, background)\n    try:\n        _post_to_control_core({\n            'client_id': row.client_id,\n            'action': 'client_created',\n            'user': None,\n            'metadata': {'name': row.name}\n        })\n    except Exception:\n        pass\n"
    # place injection after the code that adds row and commits — find the commit/refresh block
    commit_match = re.search(r"sess\.commit\(\)\s*\n\s*sess\.refresh\(row\)", new_text)
    if commit_match:
        inject_at = commit_match.end()
        new_text = new_text[:inject_at] + injection + new_text[inject_at:]
    else:
        # fallback: inject after signature
        new_text = new_text[:insert_pos] + injection + new_text[insert_pos:]

    CLIENT_FILE.write_text(new_text)
    print('Patched', CLIENT_FILE)

# Patch App Intelligence: call relay after creating event in its /api/events
def patch_app_intelligence():
    text = INTEL_FILE.read_text()
    if INSERT_MARKER in text:
        print('App intelligence already patched — skipping')
        return
    backup_path = backup(INTEL_FILE)
    print('Backed up', INTEL_FILE, '->', backup_path)
    # Insert helper after imports
    imports_end = 0
    for m in re.finditer(r"^from\s+.*|^import\s+.*", text, flags=re.M):
        imports_end = m.end()
    new_text = text[:imports_end] + relay_helper + text[imports_end:]

    # Find endpoint that creates events. In app_intelligence_app.py there is likely a POST /api/events that returns created id
    # We'll search for a function named create_event or for pattern 'POST "/api/events"'
    m = re.search(r"@app\.post\(\"/api/events\".*?\)\s*\ndef\s+(\w+)\s*\(.*?:", new_text, flags=re.S)
    if not m:
        # fallback: search for any function handling '/api/events'
        m2 = re.search(r"@app\.post\(\s*['\"]?/api/events['\"]?", new_text)
        if not m2:
            print('Could not find /api/events handler in', INTEL_FILE)
            INTEL_FILE.write_text(new_text)
            return
        func_pos = m2.end()
    else:
        func_name = m.group(1)
        # find function signature end
        func_sig = re.search(rf"def\s+{func_name}\s*\(.*?\):", new_text, flags=re.S)
        if not func_sig:
            print('Could not find function signature for', func_name)
            INTEL_FILE.write_text(new_text)
            return
        func_pos = func_sig.end()
    # inject after the DB commit/insert — look for 'sess.add(row) ... sess.commit()' pattern
    commit_match = re.search(r"sess\.commit\(\)\s*\n\s*sess\.refresh\(row\)", new_text)
    if commit_match:
        inject_at = commit_match.end()
        injection = "\n    # relay: notify Control Core about new event (best-effort, background)\n    try:\n        _post_to_control_core({\n            'client_id': row.client_id,\n            'action': row.action,\n            'user': row.user,\n            'metadata': row.metadata if hasattr(row, 'metadata') else {}\n        })\n    except Exception:\n        pass\n"
        new_text = new_text[:inject_at] + injection + new_text[inject_at:]
    else:
        # fallback inject after function signature
        injection = "\n    # relay fallback: unable to find commit point; attempting best-effort relay\n    try:\n        _post_to_control_core(payload.dict())\n    except Exception:\n        pass\n"
        new_text = new_text[:func_pos] + injection + new_text[func_pos:]

    INTEL_FILE.write_text(new_text)
    print('Patched', INTEL_FILE)

# Update .env.example files to include control core vars
def update_env_examples():
    client_env = ROOT / '.env.example'  # note: client may not have separate folder; adjust both
    app_env = ROOT / 'app_intelligence' / '.env.example'
    core_env_line = '\n# Control Core (integration)\nCC_CONTROL_CORE_URL=http://localhost:8021\nCC_SYS_API_KEY=supersecret_sys_key\n'
    for envf in [client_env, app_env]:
        if envf.exists():
            txt = envf.read_text()
            if 'CC_CONTROL_CORE_URL' not in txt:
                envf.write_text(txt + core_env_line)
                print('Updated env example:', envf)

if __name__ == '__main__':
    print('Running 3-way integration patch...')
    patch_client_customization()
    patch_app_intelligence()
    update_env_examples()
    print('\nPatch complete.\nPlease restart the three services (client customization, app intelligence, control core) in separate shells.')
