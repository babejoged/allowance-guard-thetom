"""Container entrypoint: unprivileged nginx gateway + loopback Python backend."""
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
from server import validate_public_origin


def configuration(env):
    origin = validate_public_origin(env.get('PUBLIC_ORIGIN'))
    raw = env.get('PORT', '10000')
    if not re.fullmatch(r'[1-9][0-9]{0,4}', raw):
        raise ValueError('PORT must be a decimal port')
    port = int(raw)
    if not 1024 <= port <= 65535 or port == 8765:
        raise ValueError('PORT must be 1024..65535 and different from backend port 8765')
    return origin, port


def main():
    origin, port = configuration(os.environ)
    root = Path(__file__).resolve().parent
    config = Path(tempfile.gettempdir()) / 'allowance-guard-nginx.conf'
    config.write_text((root / 'nginx.conf').read_text().replace('__PORT__', str(port)))
    subprocess.run(['nginx', '-t', '-c', str(config)], check=True)
    children = []
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        children.append(subprocess.Popen([sys.executable, str(root / 'server.py'),
                                         '--public-origin', origin]))
        children.append(subprocess.Popen(['nginx', '-c', str(config), '-g', 'daemon off;']))
        while not stopping:
            if any(child.poll() is not None for child in children):
                return 1
            time.sleep(0.2)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    sys.exit(main())
