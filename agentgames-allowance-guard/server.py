"""Stdlib demo service; deploy behind the supplied reverse proxy."""
import argparse
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from guard import assess

ROOT = Path(__file__).resolve().parent / 'web'
MAX_BODY = 16384


def unique_object(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('Duplicate JSON key')
        result[k] = v
    return result


def reject_constant(value):
    raise ValueError('Nonfinite JSON numbers are forbidden')


class Handler(BaseHTTPRequestHandler):
    server_version = 'AllowanceGuard/1.0'

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *args):
        pass  # Do not log transaction contents.

    def reply(self, status, data, content_type='application/json; charset=utf-8'):
        if not isinstance(data, bytes):
            data = json.dumps(data, separators=(',', ':')).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        self.wfile.write(data)

    def do_GET(self):
        files = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'application/javascript'), '/style.css': ('style.css', 'text/css')}
        if self.path == '/health':
            return self.reply(200, {'status': 'ok', 'policy_version': '1.0.0', 'mode': 'offline'})
        if self.path not in files:
            return self.reply(404, {'error': 'NOT_FOUND'})
        name, mime = files[self.path]
        self.reply(200, (ROOT / name).read_bytes(), mime+'; charset=utf-8')

    def expected_origin(self):
        # Vercel supplies its own request server object without local attributes.
        trusted_origin = getattr(self.server, 'trusted_origin', None)
        return trusted_origin or 'http://' + self.headers.get('Host', '')

    def do_POST(self):
        if self.path != '/api/assess':
            return self.reply(404, {'error': 'NOT_FOUND'})
        origin = self.headers.get('Origin')
        expected_origin = self.expected_origin()
        if len(self.headers.get_all('Origin', [])) > 1 or (origin is not None and origin != expected_origin):
            return self.reply(403, {'error': 'ORIGIN_REJECTED'})
        if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
            return self.reply(400, {'error': 'INVALID_BODY_FRAMING'})
        length = self.headers['Content-Length']
        if not re.fullmatch(r'0|[1-9][0-9]{0,8}', length):
            return self.reply(400, {'error': 'INVALID_CONTENT_LENGTH'})
        length = int(length)
        if length > MAX_BODY:
            return self.reply(413, {'error': 'BODY_TOO_LARGE'})
        if self.headers.get_content_type() != 'application/json':
            return self.reply(415, {'error': 'JSON_REQUIRED'})
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('Incomplete body')
            payload = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=reject_constant)
            result = assess(payload)
        except (ValueError, RecursionError) as exc:
            return self.reply(400, {'error': 'INVALID_INPUT', 'message': str(exc)[:200]})
        except TimeoutError:
            return self.reply(408, {'error': 'READ_TIMEOUT'})
        self.reply(200, result)


def validate_public_origin(trusted_origin):
    if not isinstance(trusted_origin, str) or not re.fullmatch(
            r'https://[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?(?::[1-9][0-9]{0,4})?', trusted_origin):
        raise ValueError('PUBLIC_ORIGIN must be an exact lowercase HTTPS origin without a trailing slash')
    return trusted_origin


def make_server(host='127.0.0.1', port=8765, trusted_origin=None):
    if trusted_origin is not None:
        validate_public_origin(trusted_origin)
    server = ThreadingHTTPServer((host, port), Handler)
    server.trusted_origin = trusted_origin
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--public-origin', default=os.environ.get('PUBLIC_ORIGIN'))
    args = parser.parse_args()
    with make_server(port=args.port, trusted_origin=args.public_origin) as server:
        print(f'Allowance Guard: http://127.0.0.1:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
