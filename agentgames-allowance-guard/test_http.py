"""Real loopback HTTP tests; server is shut down after the suite."""
import http.client
import importlib.util
import json
import threading
import unittest
from test_guard import tx

class HTTPTests(unittest.TestCase):
    def test_http_workflow_and_boundaries(self):
        self.assertIsNotNone(importlib.util.find_spec('server'), 'HTTP service must exist')
        from server import make_server
        server = make_server('127.0.0.1', 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def request(method, path, body=None, headers=None):
            c = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            try:
                c.request(method, path, body, headers or {})
                r = c.getresponse()
                return r.status, dict(r.getheaders()), r.read()
            finally:
                c.close()
        try:
            for path, marker in [('/', b'Allowance Guard'), ('/app.js', b'fetch'), ('/style.css', b'background')]:
                status, headers, body = request('GET', path)
                self.assertEqual(status, 200)
                self.assertIn(marker, body)
                self.assertIn('Content-Security-Policy', headers)
            self.assertEqual(request('GET', '/health')[0], 200)
            self.assertEqual(request('GET', '/../../guard.py')[0], 404)
            status, _, body = request('POST', '/api/assess', json.dumps(tx()), {'Content-Type':'application/json'})
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)['decision'], 'PASS')
            cases = [('{', {'Content-Type':'application/json'}, 400),
                     ('{"to":1,"to":2}', {'Content-Type':'application/json'}, 400),
                     ('[]', {'Content-Type':'application/json'}, 400),
                     ('NaN', {'Content-Type':'application/json'}, 400),
                     ('[]', {'Content-Type':'text/plain'}, 415),
                     ('x'*16385, {'Content-Type':'application/json'}, 413),
                     ('[]', {'Content-Type':'application/json','Origin':'https://evil.example'}, 403),
                     ('[]', {'Content-Type':'application/json','Transfer-Encoding':'chunked'}, 400)]
            for body, headers, expected in cases:
                with self.subTest(expected=expected, headers=headers):
                    self.assertEqual(request('POST', '/api/assess', body, headers)[0], expected)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_configured_https_origin_is_allowed_and_other_origins_rejected(self):
        from server import make_server
        server = make_server('127.0.0.1', 0, trusted_origin='https://demo.example')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def request(origin):
                c = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                try:
                    c.request('POST', '/api/assess', json.dumps(tx()),
                              {'Content-Type': 'application/json', 'Origin': origin})
                    r = c.getresponse()
                    return r.status, r.read()
                finally:
                    c.close()
            self.assertEqual(request('https://demo.example')[0], 200)
            self.assertEqual(request('https://evil.example')[0], 403)
            self.assertEqual(request('https://demo.example.evil')[0], 403)
            self.assertEqual(request('http://demo.example')[0], 403)
            self.assertEqual(request('null')[0], 403)
            self.assertEqual(request('')[0], 403)
            c = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            try:
                c.request('POST', '/api/assess', json.dumps(tx()), {
                    'Content-Type': 'application/json', 'Origin': 'https://evil.example',
                    'Host': 'evil.example', 'X-Forwarded-Host': 'evil.example',
                    'X-Forwarded-Proto': 'https'})
                r = c.getresponse()
                self.assertEqual(r.status, 403)
                r.read()
            finally:
                c.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

if __name__ == '__main__':
    unittest.main()
