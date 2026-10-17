"""Rebuild the Windows x64 portable application using Go (Linux or Windows)."""
from pathlib import Path
import hashlib, os, subprocess, urllib.request, zipfile

ROOT = Path(__file__).resolve().parent
RUNTIME_URL = 'https://www.python.org/ftp/python/3.13.15/python-3.13.15-embed-amd64.zip'
RUNTIME_SHA256 = 'd1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf'
archive = ROOT / 'python.zip'
if not archive.exists():
    with urllib.request.urlopen(RUNTIME_URL, timeout=60) as response:
        archive.write_bytes(response.read())
if hashlib.sha256(archive.read_bytes()).hexdigest() != RUNTIME_SHA256:
    raise SystemExit('Python runtime checksum mismatch')
with zipfile.ZipFile(ROOT / 'payload.zip', 'w', zipfile.ZIP_DEFLATED) as bundle:
    for file in sorted((ROOT / 'app').rglob('*')):
        if file.is_file() and '__pycache__' not in file.parts: bundle.write(file, file.relative_to(ROOT / 'app'))
    with zipfile.ZipFile(archive) as runtime:
        for name in runtime.namelist(): bundle.writestr('runtime/' + name, runtime.read(name))
env = {**os.environ, 'GOOS': 'windows', 'GOARCH': 'amd64', 'CGO_ENABLED': '0', 'GO111MODULE': 'off'}
subprocess.run(['go', 'build', '-trimpath', '-ldflags=-s -w', '-o', str(ROOT.parent/'dist/downloads/couchpotato.exe'), str(ROOT/'main.go')], env=env, check=True, cwd=ROOT)
