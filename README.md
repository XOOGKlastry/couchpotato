# couchpotato

Telefon z Androidem jako nowoczesny pilot do komputera Windows podłączonego
do telewizora. Sterowanie działa w domowej sieci Wi-Fi: touchpad, podgląd
ekranu, klawiatura, karty przeglądarki, YouTube, HBO Max, CANAL+, głośność,
Wake-on-LAN i opcjonalne wyłączenie po 4 godzinach bezczynności.

## Pobieranie

Gotowe aplikacje dla Windows i Androida są dostępne na stronie:
https://couchpotato-remote.ofek485388.chatgpt.site

APK 1.4 pobiera aktualny interfejs z uruchomionej aplikacji Windows, dlatego
większość aktualizacji wymaga jedynie wymiany pliku EXE na komputerze.

Static download page, signed Android 1.4 APK, Windows 1.8 x64 self-contained EXE.
Public files are in `dist`; Windows application and launcher source are in `desktop`.
The Android APK uses the existing private signing identity; no keys are included here.
Skompilowane EXE, APK i prywatny klucz podpisujący nie są przechowywane w tym
repozytorium. Repozytorium zawiera kod Windows, stronę, testy oraz rozszerzenie
Chrome/Brave. Kod Androida i jego zestaw budowania są obecnie przechowywane
oddzielnie.

Pliki maskotki `mascot.png` i `mascot.ico` są częścią gotowej paczki Windows,
ale nie są dołączone do publicznego repozytorium. Przed lokalnym budowaniem
skopiuj je z pobranej paczki do `desktop/app/`.

## Windows build

Install Go and Python on the build machine, then run `python desktop/build.py`.
The script obtains Python 3.13.15 embeddable x64 from python.org, verifies SHA-256,
and embeds its files and license alongside application code. End users need no
Go or Python installation. Update the displayed file size and SHA256SUMS.txt
after rebuilding the EXE. A new APK requires the separately retained Android build kit.

On first execution the launcher unpacks into the current user's LOCALAPPDATA,
copies itself to couchpotato/couchpotato.exe, creates a per-user Start Menu link
when permitted, and starts the local Windows server. No elevation is requested.
The server binds port 8765 and persists pairing.json separately from releases.
Closing the application stops remote control. On first launch it enables per-user autostart; the paired preferences panel can disable it. Screen frames are held only in memory and are authenticated.

## Validation

The Python tests mock Windows input. JavaScript tests exercise gesture timing,
queued-command cancellation, and UI wiring. In a test checkout, copy desktop/app
to KanapaTV and run the tests from the parent directory (the retained tests use
that original path). Native Windows and physical Android end-to-end testing has
not been performed. The Windows executable has no publisher certificate.

1.4 adds normalized-coordinate desktop clicks with stale topology rejection, full-viewport pinch/pan preview, native volume keys and offline UDP Wake-on-LAN. Hardware testing is still required.

1.5 adds a single volume rocker, YouTube 5-second seek and speed shortcuts, and per-device DOM-preserving layout customization. Layout tests use linkedom. APK 1.4 remains compatible.

1.6 replaces grid customization with independent transforms on original DOM elements, drops 10-second seek, and adds exact seven-stop speed control. The bundled MV3 Chrome/Brave extension requires one-time unpacked installation and PIN pairing. Its separate loopback-only capability can only poll/acknowledge speed commands. UI shows pending and confirmed rates. APK 1.4 remains compatible.

1.6.1 adds a capture-phase arrow-key handler on HBO Max/Max domains in the bundled extension, seeking visible finite-duration media by five seconds with seekable-range bounds and editable-field/modifier guards. Existing Windows keys and hold repeats are retained. Reload the extension after installing the updated EXE and refresh HBO tabs. Tested using a mocked video, not a logged-in HBO session.

1.7 moves the power button to the top, adds inline delete (local draft/selection, remote Backspace when empty), and replaces collapsed extra keys with permanent styled Esc/directional controls. APK 1.4 remains compatible.

1.8 adds an opt-in, persisted Windows idle monitor. After four hours without
keyboard or mouse input it starts the existing cancellable 30-second shutdown
countdown. Remote input also resets the Windows idle timer. APK 1.4 remains compatible.

## Edycja 27.10 20:30

Dodaje przycisk Polsat Box Go z oficjalną ikoną. Gotowy EXE i ZIP są dostępne
na stronie pobierania; Android APK 1.4 pozostaje zgodny. Sprawdzono uruchomienie
EXE na Windows, parowanie, uwierzytelnione połączenie, ikonę i oznaczenie edycji.

