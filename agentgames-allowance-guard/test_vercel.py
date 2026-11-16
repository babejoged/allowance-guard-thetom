"""Exercise the Vercel handler through real HTTP, without platform mocks."""
import http.client
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from http.server import ThreadingHTTPServer
from test_guard import tx


class VercelTests(unittest.TestCase):
    def test_vercel_entrypoint_serves_ui_and_enforces_https_origin(self):
        entry = Path(__file__).parent / 'api' / 'index.py'
        self.assertTrue(entry.is_file(), 'Vercel entrypoint is required')
        spec = importlib.util.spec_from_file_location('vercel_entry', entry)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        server = ThreadingHTTPServer(('127.0.0.1', 0), module.handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def request(method, path, body=None, headers=None):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            try:
                conn.request(method, path, body, headers or {})
                response = conn.getresponse()
                return response.status, response.read()
            finally:
                conn.close()
        try:
            for path, marker in [('/', b'Allowance Guard'), ('/app.js', b'fetch'),
                                 ('/style.css', b'background'), ('/health', b'offline')]:
                status, body = request('GET', path)
                self.assertEqual(status, 200)
                self.assertIn(marker, body)
            payload = json.dumps(tx())
            for origin, expected in [('https://allowance-guard-thetom.vercel.app', 200),
                                     ('https://evil.example', 403), ('null', 403)]:
                status, body = request('POST', '/api/assess', payload, {
                    'Content-Type': 'application/json', 'Origin': origin,
                    'Host': 'evil.example', 'X-Forwarded-Host': 'evil.example'})
                self.assertEqual(status, expected)
                if status == 200:
                    from guard import assess
                    self.assertEqual(json.loads(body), assess(tx()))
                else:
                    self.assertEqual(json.loads(body)['error'], 'ORIGIN_REJECTED')
            self.assertEqual(request('POST', '/api/assess', payload,
                                    {'Content-Type': 'application/json'})[0], 200)
            self.assertEqual(request('POST', '/api/assess', '{',
                                    {'Content-Type': 'application/json'})[0], 400)
            self.assertEqual(request('GET', '/guard.py')[0], 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
