"""Local-only launcher; the employer sandbox API is opt-in via ME_EMPLOYER_LOCAL_API."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent
os.chdir(BASE)
runtime = BASE / '.runtime'
runtime.mkdir(exist_ok=True)
socket = runtime / 'pgsocket'
socket.mkdir(mode=0o700, exist_ok=True)
socket.chmod(0o700)
data = runtime / 'pgdata'
for command in ['initdb', 'pg_ctl', 'createdb', 'psql']:
    if not shutil.which(command):
        raise SystemExit(f'Missing local prerequisite: {command}')
env = {**os.environ, 'PGHOST': str(socket), 'PGPORT': '55432', 'PGDATABASE': 'me_local', 'ME_DEMO_MODE': '1'}
if not data.exists():
    subprocess.run(['initdb', '-D', str(data), '-A', 'trust', '--no-locale', '-E', 'UTF8'], check=True)
if subprocess.run(['pg_ctl', '-D', str(data), 'status'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
    options = f"-k '{socket}' -p 55432 -c listen_addresses=''"
    subprocess.run(['pg_ctl', '-D', str(data), '-l', str(runtime / 'postgres.log'), '-o', options, 'start'], check=True)
exists = subprocess.run(['psql', '-d', 'postgres', '-tAc', "SELECT 1 FROM pg_database WHERE datname = 'me_local'"],
                        env=env, capture_output=True, text=True, check=True).stdout.strip()
if exists != '1':
    subprocess.run(['createdb', 'me_local'], env=env, check=True)
for args in [['migrate', '--noinput'], ['seed_demo']]:
    subprocess.run([sys.executable, 'manage.py', *args], env=env, check=True)
port = int(os.environ.get('ME_LOCAL_PORT', '8014'))
if not 1024 <= port <= 65535:
    raise SystemExit('Invalid local port')
subprocess.run([sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'], env=env, check=True)
