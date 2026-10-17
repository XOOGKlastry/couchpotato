"""Local Windows startup preferences and on-demand screen preview. No disk captures."""
import ctypes as c
from ctypes import wintypes as w
import json, os, struct, zlib
from pathlib import Path

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
PREFERENCES_FILE = 'preferences.json'

def startup(enabled=None):
    import winreg
    launcher = Path(os.environ['LOCALAPPDATA']) / 'couchpotato' / 'couchpotato.exe'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled is True:
            if not launcher.is_file(): raise OSError('Najpierw uruchom couchpotato.exe.')
            command = f'"{launcher}" --startup'
            if len(command) > 260: raise OSError('Sciezka aplikacji jest zbyt dluga.')
            winreg.SetValueEx(key, 'couchpotato', 0, winreg.REG_SZ, command)
        elif enabled is False:
            try: winreg.DeleteValue(key, 'couchpotato')
            except FileNotFoundError: pass
        try: value, _ = winreg.QueryValueEx(key, 'couchpotato')
        except FileNotFoundError: value = ''
    return bool(value), launcher.is_file()

def init_startup():
    marker = Path(os.environ['LOCALAPPDATA']) / 'couchpotato' / 'startup-configured'
    if not marker.exists() and startup()[1]:
        startup(True)
        marker.write_text('1', encoding='ascii')

def idle_shutdown(enabled=None):
    """Persist the opt-in four-hour idle shutdown preference."""
    directory = Path(os.environ['LOCALAPPDATA']) / 'couchpotato'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / PREFERENCES_FILE
    value = False
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or type(data.get('idle_shutdown', False)) is not bool:
            raise ValueError('Nieprawidlowe ustawienia couchpotato.')
        value = data.get('idle_shutdown', False)
    if enabled is not None:
        if type(enabled) is not bool: raise ValueError('Nieprawidlowa opcja bezczynnosci.')
        value = enabled
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'idle_shutdown': value}), encoding='utf-8')
        os.replace(temporary, path)
    return value

def idle_seconds():
    """Seconds since the last physical keyboard or mouse input in Windows."""
    class LASTINPUTINFO(c.Structure):
        _fields_ = [('cbSize', w.UINT), ('dwTime', w.DWORD)]
    info = LASTINPUTINFO(c.sizeof(LASTINPUTINFO), 0)
    user = c.WinDLL('user32', use_last_error=True)
    if not user.GetLastInputInfo(c.byref(info)):
        raise OSError('Nie mozna odczytac czasu bezczynnosci.')
    kernel = c.WinDLL('kernel32', use_last_error=True)
    kernel.GetTickCount.restype = w.DWORD
    return ((kernel.GetTickCount() - info.dwTime) & 0xffffffff) / 1000

def png_rgb(width, height, rgb):
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    scan = b''.join(b'\0' + rgb[y*width*3:(y+1)*width*3] for y in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(scan, 3)) + chunk(b'IEND', b'')

def bounds():
    u=c.WinDLL('user32',use_last_error=True)
    return [u.GetSystemMetrics(i) for i in (76,77,78,79)]

def click_at(x,y,geometry):
    import math
    if type(x) not in (int,float) or type(y) not in (int,float) or not math.isfinite(x) or not math.isfinite(y) or not 0<=x<=1 or not 0<=y<=1:
        raise ValueError('Nieprawidlowe wspolrzedne')
    current=bounds()
    if geometry != current or current[2]<=0 or current[3]<=0: raise ValueError('Uklad ekranow zmienil sie. Odswiez podglad.')
    u=c.WinDLL('user32',use_last_error=True)
    if not u.SetCursorPos(current[0]+round(x*(current[2]-1)),current[1]+round(y*(current[3]-1))):raise OSError('Nie mozna ustawic kursora')
    u.mouse_event(2,0,0,0,0);u.mouse_event(4,0,0,0,0)

def capture(detail=False):
    user, gdi = c.WinDLL('user32', use_last_error=True), c.WinDLL('gdi32', use_last_error=True)
    # Explicit pointer types are essential for 64-bit GDI handles.
    user.GetDC.argtypes=[w.HWND]; user.GetDC.restype=w.HDC
    user.ReleaseDC.argtypes=[w.HWND,w.HDC]
    gdi.CreateCompatibleDC.argtypes=[w.HDC]; gdi.CreateCompatibleDC.restype=w.HDC
    gdi.CreateCompatibleBitmap.argtypes=[w.HDC,c.c_int,c.c_int]; gdi.CreateCompatibleBitmap.restype=w.HBITMAP
    gdi.SelectObject.argtypes=[w.HDC,w.HGDIOBJ]; gdi.SelectObject.restype=w.HGDIOBJ
    gdi.DeleteObject.argtypes=[w.HGDIOBJ]; gdi.DeleteDC.argtypes=[w.HDC]
    gdi.StretchBlt.argtypes=[w.HDC,c.c_int,c.c_int,c.c_int,c.c_int,w.HDC,c.c_int,c.c_int,c.c_int,c.c_int,w.DWORD]
    gdi.GetDIBits.argtypes=[w.HDC,w.HBITMAP,w.UINT,w.UINT,c.c_void_p,c.c_void_p,w.UINT]
    gdi.SetStretchBltMode.argtypes=[w.HDC,c.c_int]
    # Entire desktop includes the TV when using an extended desktop.
    x,y,sw,sh = [user.GetSystemMetrics(i) for i in (76,77,78,79)]
    if sw <= 0 or sh <= 0: raise OSError('Ekran jest niedostepny.')
    scale=min(1, (2560 if detail else 1120)/sw, (1600 if detail else 720)/sh); width=max(1,int(sw*scale)); height=max(1,int(sh*scale))
    screen=dc=bitmap=old=None
    try:
        screen=user.GetDC(None)
        if not screen: raise OSError('Brak dostepu do ekranu.')
        dc=gdi.CreateCompatibleDC(screen); bitmap=gdi.CreateCompatibleBitmap(screen,width,height)
        if not dc or not bitmap: raise OSError('Nie mozna utworzyc podgladu.')
        old=gdi.SelectObject(dc,bitmap)
        if not old or old == c.c_void_p(-1).value: raise OSError('Nie mozna wybrac bitmapy.')
        gdi.SetStretchBltMode(dc,4)
        if not gdi.StretchBlt(dc,0,0,width,height,screen,x,y,sw,sh,0x00CC0020): raise OSError('Ekran jest niedostepny.')
        gdi.SelectObject(dc,old); old=None
        info=c.create_string_buffer(struct.pack('<IiiHHIIiiII',40,width,-height,1,32,0,0,0,0,0,0))
        pixels=c.create_string_buffer(width*height*4)
        if gdi.GetDIBits(screen,bitmap,0,height,pixels,info,0) != height: raise OSError('Nie mozna odczytac ekranu.')
        bgra=pixels.raw; rgb=bytearray(width*height*3)
        rgb[0::3]=bgra[2::4]; rgb[1::3]=bgra[1::4]; rgb[2::3]=bgra[0::4]
        return png_rgb(width,height,rgb)
    finally:
        if old and dc: gdi.SelectObject(dc,old)
        if bitmap: gdi.DeleteObject(bitmap)
        if dc: gdi.DeleteDC(dc)
        if screen: user.ReleaseDC(None,screen)
