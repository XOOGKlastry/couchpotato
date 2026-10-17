"""couchpotato — Windows, Python 3.10+, standard library only."""
import ctypes
from ctypes import wintypes as W
import hmac
import ipaddress
import json
import math
import ntpath
import os
from pathlib import Path
import secrets
import socket
import subprocess
import threading
import time
import webbrowser
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import desktop_features
import youtube_bridge
from urllib.parse import urlsplit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
PORT = 8765
CODE = f'{secrets.randbelow(10000):04d}'
TOKEN = secrets.token_urlsafe(32)
SERVICES = {'youtube': 'https://www.youtube.com/', 'hbo': 'https://www.hbomax.com/', 'canal': 'https://www.canalplus.com/pl/'}
KEYS = {'enter': 13, 'space': 32, 'esc': 27, 'tab': 9, 'backspace': 8, 'left': 37, 'up': 38, 'right': 39, 'down': 40, 'fullscreen': 70, 'browser_fullscreen': 122, 'seek5_back': 37, 'seek5_forward': 39, 'youtube_play': 75, 'volup': 175, 'voldown': 174, 'mute': 173, 'play': 179, 'back': 166}
SHORTCUTS = {'tab_left': (17, 16, 9), 'tab_right': (17, 9), 'alt_tab': (18, 9), 'close_tab': (17, 87), 'address_bar': (17, 76)}
LOCK = threading.Lock()
ATTEMPTS = []
YOUTUBE = youtube_bridge.Bridge()
PAIR_WINDOW = 300
PAIR_LIMIT = 5

def load_pairing(directory=None):
    """One code and revocable bearer secret per Windows account, across updates."""
    directory = Path(directory) if directory is not None else Path(os.environ['LOCALAPPDATA']) / 'couchpotato'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'pairing.json'
    if not path.exists():
        value = {'code': f'{secrets.randbelow(10000):04d}', 'token': secrets.token_urlsafe(32)}
        # Exclusive create: a second launcher must never replace an existing PIN.
        try:
            with path.open('x', encoding='utf-8') as file:
                json.dump(value, file)
                file.flush()
                os.fsync(file.fileno())
        except FileExistsError:
            pass
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Nieprawidlowy plik pairing.json.')
    code, token = value.get('code'), value.get('token')
    if not isinstance(code, str) or len(code) != 4 or not code.isascii() or not code.isdigit() or not isinstance(token, str) or len(token) < 40:
        raise ValueError('Nieprawidlowy zapisany kod. Przywroc plik pairing.json z kopii lub usun go, aby ustawic nowy kod.')
    return code, token

class ActionError(OSError):
    """A fixed, user-facing error, never raw system output."""

class Windows:
    def __init__(self):
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        self.u.SetProcessDPIAware()
        ULONG_PTR = ctypes.c_size_t
        class MI(ctypes.Structure):
            _fields_ = [('dx', W.LONG), ('dy', W.LONG), ('mouseData', W.DWORD), ('dwFlags', W.DWORD), ('time', W.DWORD), ('extra', ULONG_PTR)]
        class KI(ctypes.Structure):
            _fields_ = [('vk', W.WORD), ('scan', W.WORD), ('flags', W.DWORD), ('time', W.DWORD), ('extra', ULONG_PTR)]
        class U(ctypes.Union):
            _fields_ = [('mi', MI), ('ki', KI)]
        class INPUT(ctypes.Structure):
            _anonymous_ = ('data',)
            _fields_ = [('type', W.DWORD), ('data', U)]
        self.INPUT, self.KI = INPUT, KI
        self.u.SendInput.argtypes = [W.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        self.u.SendInput.restype = W.UINT
        self.k = ctypes.WinDLL('kernel32', use_last_error=True)
        self.u.GetForegroundWindow.restype = W.HWND
        self.u.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
        self.u.IsWindowVisible.argtypes = [W.HWND]
        self.u.IsIconic.argtypes = [W.HWND]
        self.u.ShowWindowAsync.argtypes = [W.HWND, ctypes.c_int]
        self.u.SetForegroundWindow.argtypes = [W.HWND]
        self.k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        self.k.OpenProcess.restype = W.HANDLE
        self.k.CloseHandle.argtypes = [W.HANDLE]
        self.k.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, ctypes.POINTER(W.DWORD)]
        self.enum_callback = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        self.u.EnumWindows.argtypes = [self.enum_callback, W.LPARAM]
    def is_chrome(self, window):
        if not window:
            return False
        pid = W.DWORD()
        self.u.GetWindowThreadProcessId(window, ctypes.byref(pid))
        process = self.k.OpenProcess(0x1000, False, pid.value)
        if not process:
            return False
        try:
            name = ctypes.create_unicode_buffer(32768)
            size = W.DWORD(len(name))
            return bool(self.k.QueryFullProcessImageNameW(process, 0, name, ctypes.byref(size))) and ntpath.basename(name.value).lower() == 'chrome.exe'
        finally:
            self.k.CloseHandle(process)
    def focus_chrome(self):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if self.is_chrome(self.u.GetForegroundWindow()):
                return
            windows = []
            @self.enum_callback
            def visit(window, _):
                if self.u.IsWindowVisible(window) and self.is_chrome(window):
                    windows.append(window)
                return True
            self.u.EnumWindows(visit, 0)
            if windows:
                if self.u.IsIconic(windows[0]):
                    self.u.ShowWindowAsync(windows[0], 9)
                self.u.SetForegroundWindow(windows[0])
                if self.is_chrome(self.u.GetForegroundWindow()):
                    return
            time.sleep(0.08)
        raise ActionError('Chrome jest otwarty, ale Windows nie pozwolił go uaktywnić. Wybierz okno Chrome i spróbuj ponownie.')
    def key(self, name):
        key = KEYS[name]
        self.u.keybd_event(key, 0, 0, 0)
        self.u.keybd_event(key, 0, 2, 0)
    def shortcut(self, name):
        pressed = []
        try:
            for key in SHORTCUTS[name]:
                self.u.keybd_event(key, 0, 0, 0)
                pressed.append(key)
        finally:
            for key in reversed(pressed):
                self.u.keybd_event(key, 0, 2, 0)
    def text(self, value):
        raw = value.encode('utf-16-le')
        for i in range(0, len(raw), 2):
            unit = int.from_bytes(raw[i:i+2], 'little')
            events = (self.INPUT * 2)()
            for j, flags in enumerate((4, 6)):
                events[j].type = 1
                events[j].ki = self.KI(0, unit, flags, 0, 0)
            if self.u.SendInput(2, events, ctypes.sizeof(self.INPUT)) != 2:
                raise OSError('Windows nie przyjal tekstu')
    def move(self, dx, dy):
        self.u.mouse_event(1, dx, dy, 0, 0)
    def click(self):
        self.u.mouse_event(2, 0, 0, 0, 0)
        self.u.mouse_event(4, 0, 0, 0, 0)
    def right_click(self):
        self.u.mouse_event(8, 0, 0, 0, 0)
        self.u.mouse_event(16, 0, 0, 0, 0)
    def open_link_tab(self):
        # Middle click opens the link under the pointer in a background tab.
        self.u.mouse_event(0x20, 0, 0, 0, 0)
        self.u.mouse_event(0x40, 0, 0, 0, 0)
    def scroll(self, delta):
        self.u.mouse_event(0x800, 0, 0, delta, 0)
    def shutdown(self):
        # The countdown lives in Python. Windows /t > 0 implies /f, which
        # would force-close unsaved work. Never use /f or a positive /t here.
        executable = Path(os.environ['SystemRoot']) / 'System32' / 'shutdown.exe'
        result = subprocess.run([str(executable), '/s', '/t', '0'],
                                capture_output=True, timeout=10,
                                creationflags=0x08000000, shell=False)
        if result.returncode:
            raise OSError('Windows odrzucil wylaczenie komputera')

CONTROL = None

class PowerManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.timer = None
        self.deadline = 0
        self.state = 'idle'
        self.generation = 0
    def schedule(self):
        with self.lock:
            if self.state in ('countdown', 'sent'):
                return
            self.generation += 1
            self.deadline = time.monotonic() + 30
            self.state = 'countdown'
            self.timer = threading.Timer(30, self.finish, args=(self.generation,))
            self.timer.daemon = True
            self.timer.start()
    def finish(self, generation):
        with self.lock:
            if self.state != 'countdown' or generation != self.generation:
                return
            self.state = 'sent'
            try:
                CONTROL.shutdown()
            except (OSError, subprocess.SubprocessError):
                self.state = 'error'
    def cancel(self):
        with self.lock:
            if self.state == 'sent':
                raise ValueError('Wylaczanie juz przekazano do Windows')
            if self.timer:
                self.timer.cancel()
            self.generation += 1
            self.state = 'idle'
            self.deadline = 0
    def status(self):
        with self.lock:
            return {'state': self.state, 'seconds': max(0, math.ceil(self.deadline - time.monotonic())) if self.state == 'countdown' else 0}

POWER = PowerManager()

class IdleShutdownMonitor:
    LIMIT = 4 * 60 * 60
    def __init__(self, power, idle=desktop_features.idle_seconds, interval=30):
        self.power, self.idle, self.interval = power, idle, interval
        self.stop_event = threading.Event()
        self.fired = False
        self.thread = None
    def check(self):
        enabled = desktop_features.idle_shutdown()
        seconds = self.idle()
        if not enabled or seconds < self.LIMIT:
            self.fired = False
        elif not self.fired:
            self.fired = True
            self.power.schedule()
        return {'enabled': enabled, 'idle_seconds': int(seconds)}
    def run(self):
        while not self.stop_event.wait(self.interval):
            try: self.check()
            except (OSError, ValueError, json.JSONDecodeError): pass
    def start(self):
        self.thread = threading.Thread(target=self.run, name='couchpotato-idle-shutdown', daemon=True)
        self.thread.start()
    def stop(self):
        self.stop_event.set()

IDLE = IdleShutdownMonitor(POWER)

def brave_open(url):
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) < 33 for c in url):
        raise ValueError('Nieprawidlowy adres')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Wymagany adres HTTPS')
    candidates = [Path(os.environ[root]) / 'BraveSoftware' / 'Brave-Browser' / 'Application' / 'brave.exe'
                  for root in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA') if os.environ.get(root)]
    executable = next((str(path) for path in candidates if path.is_file()), None)
    executable = executable or shutil.which('brave.exe')
    if not executable:
        raise FileNotFoundError('Brave nie jest zainstalowany')
    subprocess.Popen([executable, '--new-tab', url], shell=False)

def chrome_new_tab():
    candidates = [Path(os.environ[root]) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe'
                  for root in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA') if os.environ.get(root)]
    executable = next((str(path) for path in candidates if path.is_file()), None) or shutil.which('chrome.exe')
    if not executable:
        raise ActionError('Nie znaleziono Chrome na laptopie. Zainstaluj Google Chrome.')
    subprocess.Popen([executable, '--new-tab', 'chrome://newtab/'], shell=False)
    CONTROL.focus_chrome()
    CONTROL.shortcut('address_bar')

def execute(data):
    action = data.get('action')
    if action == 'open' and isinstance(data.get('service'), str) and data['service'] in SERVICES:
        if not webbrowser.open(SERVICES[data['service']], new=2):
            raise OSError('Nie mozna otworzyc przegladarki')
    elif action == 'key' and isinstance(data.get('key'), str) and data['key'] in KEYS:
        CONTROL.key(data['key'])
    elif action == 'shortcut' and isinstance(data.get('shortcut'), str) and data['shortcut'] in SHORTCUTS:
        CONTROL.shortcut(data['shortcut'])
    elif action == 'open_brave':
        brave_open(data.get('url'))
    elif action == 'new_chrome_tab':
        chrome_new_tab()
    elif action == 'chrome_search' and isinstance(data.get('text'), str) and 0 < len(data['text']) <= 500:
        CONTROL.focus_chrome()
        CONTROL.shortcut('address_bar')
        CONTROL.text(data['text'])
        CONTROL.key('enter')
    elif action == 'text' and isinstance(data.get('text'), str) and 0 < len(data['text']) <= 500:
        CONTROL.text(data['text'])
    elif action == 'move' and all(type(data.get(k)) is int and abs(data[k]) <= 300 for k in ('dx', 'dy')):
        CONTROL.move(data['dx'], data['dy'])
    elif action == 'playback_rate':
        try: YOUTUBE.set_rate(data.get('rate'))
        except OSError as error: raise ActionError(str(error))
    elif action == 'extension_folder':
        os.startfile(str(Path(os.environ['LOCALAPPDATA']) / 'couchpotato' / 'youtube-extension'))
    elif action == 'screen_click':
        desktop_features.click_at(data.get('x'),data.get('y'),data.get('bounds'))
    elif action == 'right_click':
        CONTROL.right_click()
    elif action == 'open_link_tab':
        CONTROL.open_link_tab()
    elif action == 'click':
        CONTROL.click()
    elif action == 'scroll' and type(data.get('delta')) is int and abs(data['delta']) <= 2400:
        CONTROL.scroll(data['delta'])
    elif action == 'shutdown' and data.get('confirmed') is True:
        POWER.schedule()
    elif action == 'cancel_shutdown':
        POWER.cancel()
    else:
        raise ValueError('Nieprawidlowe polecenie')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not log pairing codes, tokens or typed text.
    def setup(self):
        super().setup()
        self.connection.settimeout(5)
    def reply(self, status, body, mime='application/json; charset=utf-8', headers=None):
        raw = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(status)
        self.send_header('Content-Type', mime)
        for name, value in (headers or {}).items(): self.send_header(name,value)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)
    def valid_host(self):
        return self.headers.get('Host') in self.server.allowed_hosts
    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, '{}')
        if self.path == '/setup' and ipaddress.ip_address(self.client_address[0]).is_loopback:
            return self.reply(200, json.dumps({'code': CODE, 'addresses': self.server.addresses}))
        files = {'/layout-editor.js': ('layout-editor.js', 'text/javascript; charset=utf-8'), '/viewer.js': ('viewer.js', 'text/javascript; charset=utf-8'), '/extras.js': ('extras.js', 'text/javascript; charset=utf-8'), '/mascot.png': ('mascot.png', 'image/png'), '/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/gestures.js': ('gestures.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if self.path not in files:
            return self.reply(404, '{}')
        file, mime = files[self.path]
        self.reply(200, (ROOT / file).read_bytes() if mime.startswith('image/') else (ROOT / file).read_text(encoding='utf-8'), mime)
    def do_POST(self):
        origin = self.headers.get('Origin')
        extension_request = self.path in ('/extension/pair', '/extension/poll')
        local = ipaddress.ip_address(self.client_address[0]).is_loopback
        extension_origin = origin is not None and origin.startswith('chrome-extension://') and len(origin.split('://',1)[1]) == 32 and all(c in 'abcdefghijklmnop' for c in origin.split('://',1)[1])
        if extension_request and not local:
            return self.reply(403, '{}')
        if not self.valid_host() or (origin is not None and origin != 'http://' + self.headers.get('Host', '') and not (extension_request and local and extension_origin)):
            return self.reply(403, '{}')
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.reply(415, '{}')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 8192:
                return self.reply(413, '{}')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError()
        except (ValueError, OSError):
            return self.reply(400, '{}')
        with LOCK:
            if self.path in ('/pair','/extension/pair'):
                now = time.monotonic()
                ATTEMPTS[:] = [t for t in ATTEMPTS if now - t < PAIR_WINDOW]
                if len(ATTEMPTS) >= PAIR_LIMIT:
                    return self.reply(429, '{}')
                candidate = data.get('code')
                if isinstance(candidate, str) and candidate.isascii() and hmac.compare_digest(candidate, CODE):
                    return self.reply(200, json.dumps({'token': youtube_bridge.extension_token(TOKEN) if extension_request else TOKEN}))
                ATTEMPTS.append(now)
                return self.reply(403, '{}')
            if self.path == '/extension/poll':
                expected = 'Bearer ' + youtube_bridge.extension_token(TOKEN)
                if not hmac.compare_digest(self.headers.get('Authorization','').encode('utf-8'),expected.encode('ascii')):
                    return self.reply(401, '{}')
                try: return self.reply(200, json.dumps(YOUTUBE.poll(data)))
                except ValueError: return self.reply(400, '{}')
            if not hmac.compare_digest(self.headers.get('Authorization', '').encode('utf-8'), ('Bearer ' + TOKEN).encode('ascii')):
                return self.reply(401, '{}')
            if self.path == '/preview':
                try:
                    geometry = desktop_features.bounds()
                    frame = desktop_features.capture(data.get('detail') is True)
                    if desktop_features.bounds() != geometry: raise OSError('Ekrany zmienione')
                    return self.reply(200, frame, 'image/png', {'X-Screen-Bounds': json.dumps(geometry)})
                except OSError:
                    return self.reply(503, json.dumps({'error': 'Podgląd niedostępny. Sprawdź, czy ekran Windows jest odblokowany.'}))
            if self.path == '/preferences':
                try:
                    value = data.get('startup')
                    if value is not None and type(value) is not bool: raise ValueError()
                    idle_value = data.get('idle_shutdown')
                    if idle_value is not None and type(idle_value) is not bool: raise ValueError()
                    enabled, available = desktop_features.startup(value)
                    idle_enabled = desktop_features.idle_shutdown(idle_value)
                    return self.reply(200, json.dumps({'startup': enabled, 'available': available, 'idle_shutdown': idle_enabled}))
                except ValueError:
                    return self.reply(400, '{}')
                except OSError:
                    return self.reply(500, json.dumps({'error': 'Nie udało się zmienić autostartu. Uruchom wydanie EXE na laptopie.'}))
            if self.path == '/ping':
                return self.reply(200, json.dumps({'power': POWER.status(), 'youtube': YOUTUBE.state()}))
            if self.path != '/action':
                return self.reply(404, '{}')
            try:
                execute(data)
            except (ValueError, KeyError):
                return self.reply(400, '{}')
            except ActionError as error:
                return self.reply(500, json.dumps({'error': str(error)}))
            except FileNotFoundError:
                return self.reply(500, json.dumps({'error': 'Nie znaleziono Brave na laptopie. Zainstaluj Brave i spróbuj ponownie.'}))
            except OSError:
                return self.reply(500, '{}')
            return self.reply(200, json.dumps({'power': POWER.status(), 'youtube': YOUTUBE.state()}))

def addresses():
    found = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith('127.'):
                found.add(ip)
    except OSError:
        pass
    return sorted(found)

def main():
    global CONTROL, CODE, TOKEN
    if os.name != 'nt':
        raise SystemExit('Ta aplikacja wymaga Windows 10 lub 11.')
    CONTROL = Windows()
    ips = addresses()
    try:
        server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    except OSError as error:
        raise SystemExit('Nie mozna uruchomic portu 8765. Zamknij druga kopie aplikacji. ' + str(error))
    try:
        CODE, TOKEN = load_pairing()
        shutil.copytree(ROOT / 'youtube-extension', Path(os.environ['LOCALAPPDATA']) / 'couchpotato' / 'youtube-extension', dirs_exist_ok=True)
    except (OSError, ValueError, KeyError) as error:
        server.server_close()
        raise SystemExit('Nie mozna odczytac stalego kodu: ' + str(error))
    server.allowed_hosts = {f'{ip}:{PORT}' for ip in ips + ['127.0.0.1', 'localhost']}
    server.addresses = [f'http://{ip}:{PORT}' for ip in ips]
    print('\nCOUCHPOTATO — pozostaw to okno otwarte. Ctrl+C zatrzymuje pilot.\n')
    print('Kod telefonu:', CODE)
    for address in server.addresses:
        print('Adres telefonu:', address)
    try:
        desktop_features.init_startup()
    except OSError:
        print('Autostart niedostepny. Wlacz go pozniej w ustawieniach pilota.')
    IDLE.start()
    if os.environ.get('COUCHPOTATO_STARTUP') != '1':
        webbrowser.open(f'http://127.0.0.1:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        IDLE.stop()
        try:
            POWER.cancel()
        except ValueError:
            pass
        server.server_close()

if __name__ == '__main__':
    main()
