"""Repack the embedded payload in the retained Windows launcher.

This is used when rebuilding on a host without Go. The replacement ZIP is
padded to the exact embedded slice length, so the launcher's compiled bounds
and executable signature layout remain intact.
"""
from io import BytesIO
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parent
EXE = ROOT.parent / 'dist' / 'downloads' / 'couchpotato.exe'
APP = ROOT / 'app'


def embedded_archive(binary):
    position = 0
    candidates = []
    while True:
        end = binary.find(b'PK\x05\x06', position)
        if end < 0: break
        position = end + 4
        if end + 22 > len(binary): continue
        comment = struct.unpack_from('<H', binary, end + 20)[0]
        directory_size = struct.unpack_from('<I', binary, end + 12)[0]
        directory_offset = struct.unpack_from('<I', binary, end + 16)[0]
        start = end - directory_size - directory_offset
        finish = end + 22 + comment
        if start >= 0 and binary[start:start + 4] == b'PK\x03\x04':
            try:
                with zipfile.ZipFile(BytesIO(binary[start:finish])) as archive:
                    names = archive.namelist()
                if 'runtime/python.exe' in names and 'app.py' in names:
                    candidates.append((start, finish))
            except zipfile.BadZipFile:
                pass
    if len(candidates) != 1: raise SystemExit('Nie znaleziono jednego osadzonego pakietu.')
    return candidates[0]


binary = EXE.read_bytes()
start, finish = embedded_archive(binary)
old_payload = binary[start:finish]
with zipfile.ZipFile(BytesIO(old_payload)) as old:
    runtime = {name: old.read(name) for name in old.namelist() if name.startswith('runtime/')}

output = BytesIO()
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
    for file in sorted(APP.rglob('*')):
        if file.is_file() and '__pycache__' not in file.parts:
            bundle.write(file, file.relative_to(APP))
    for name, data in runtime.items(): bundle.writestr(name, data)
new_payload = output.getvalue()
padding = len(old_payload) - len(new_payload)
if padding < 0 or padding > 65535:
    raise SystemExit(f'Nowy pakiet nie miesci sie w launcherze ({-padding:+d} bajtow ponad limit).')
with zipfile.ZipFile(output, 'a') as bundle: bundle.comment = b'\0' * padding
new_payload = output.getvalue()
if len(new_payload) != len(old_payload): raise SystemExit('Nieprawidlowy rozmiar pakietu.')
EXE.write_bytes(binary[:start] + new_payload + binary[finish:])
with zipfile.ZipFile(BytesIO(new_payload)) as bundle:
    if bundle.testzip() is not None: raise SystemExit('Uszkodzony pakiet wynikowy.')
print('Gotowe:', EXE)
