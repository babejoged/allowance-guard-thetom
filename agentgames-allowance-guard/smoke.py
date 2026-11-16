"""Exercise the real CLI server; no remote calls or persistent processes."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from test_guard import tx

root = Path(__file__).resolve().parent
env = dict(os.environ, PUBLIC_ORIGIN='https://demo.example')
process = subprocess.Popen([sys.executable, str(root / 'server.py'), '--port', '0'],
                           env=env, stdout=subprocess.PIPE, text=True)
try:
    line = process.stdout.readline().strip()
    port = int(line.rsplit(':', 1)[1])
    for path, origin, expected in [('/health', None, 200), ('/', None, 200),
                                    ('/api/assess', 'https://demo.example', 200),
                                    ('/api/assess', 'https://evil.example', 403)]:
        c = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        try:
            headers = {'Content-Type': 'application/json'}
            if origin:
                headers['Origin'] = origin
            c.request('POST' if origin else 'GET', path,
                      json.dumps(tx()) if origin else None, headers)
            r = c.getresponse()
            body = r.read()
            assert r.status == expected, (path, r.status, body)
            if origin == 'https://demo.example':
                result = json.loads(body)
                assert result['decision'] == 'PASS' and result['remediation']
            print(f'{path} Origin={origin} -> {r.status}')
        finally:
            c.close()
finally:
    process.terminate()
    process.wait(timeout=10)
    process.stdout.close()
