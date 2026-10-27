package main

import (
 "archive/zip"
 "bufio"
 "bytes"
 "crypto/sha256"
 _ "embed"
 "fmt"
 "io"
 "os"
 "os/exec"
 "path/filepath"
 "strings"
 "syscall"
 "unsafe"
)

//go:embed payload.zip
var payload []byte

func fail(err error) {
 fmt.Println("\nNie udalo sie uruchomic couchpotato:", err)
 fmt.Println("Nacisnij Enter, aby zamknac.")
 bufio.NewReader(os.Stdin).ReadString('\n')
 os.Exit(1)
}

func unpack(root string) (string, error) {
 digest := sha256.Sum256(payload)
 target := filepath.Join(root, "releases", fmt.Sprintf("%x", digest[:8]))
 if _, err := os.Stat(filepath.Join(target, ".complete")); err == nil { return target, nil }
 if err := os.MkdirAll(filepath.Dir(target), 0700); err != nil { return "", err }
 temp, err := os.MkdirTemp(filepath.Dir(target), "prepare-")
 if err != nil { return "", err }
 defer os.RemoveAll(temp)
 reader, err := zip.NewReader(bytes.NewReader(payload), int64(len(payload)))
 if err != nil { return "", err }
 for _, f := range reader.File {
  name := filepath.FromSlash(f.Name)
  if !filepath.IsLocal(name) || f.Mode() & os.ModeSymlink != 0 { return "", fmt.Errorf("nieprawidlowy plik pakietu") }
  path := filepath.Join(temp, name)
  if f.FileInfo().IsDir() { if err := os.MkdirAll(path, 0700); err != nil { return "", err }; continue }
  if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil { return "", err }
  src, err := f.Open(); if err != nil { return "", err }
  dst, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
  if err != nil { src.Close(); return "", err }
  _, copyErr := io.Copy(dst, src)
  src.Close(); closeErr := dst.Close()
  if copyErr != nil { return "", copyErr }; if closeErr != nil { return "", closeErr }
 }
 if err := os.WriteFile(filepath.Join(temp, ".complete"), []byte("2026-10-27-2030"), 0600); err != nil { return "", err }
 if err := os.Rename(temp, target); err != nil { return "", err }
 return target, nil
}

func installLauncher(root, release string) error {
 src, err := os.Executable(); if err != nil { return err }
 dst := filepath.Join(root, "couchpotato.exe")
 if !strings.EqualFold(filepath.Clean(src), filepath.Clean(dst)) {
  input, err := os.Open(src); if err != nil { return err }; defer input.Close()
  output, err := os.Create(dst + ".new"); if err != nil { return err }
  _, copyErr := io.Copy(output, input); closeErr := output.Close()
  if copyErr != nil { return copyErr }; if closeErr != nil { return closeErr }
  if err := os.Rename(dst + ".new", dst); err != nil { return err }
 }
 // Pass paths via environment rather than interpolating executable script text.
 ps := exec.Command(filepath.Join(os.Getenv("SystemRoot"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe"), "-NoProfile", "-NonInteractive", "-Command", `$w=New-Object -ComObject WScript.Shell; $p=Join-Path ([Environment]::GetFolderPath('Programs')) 'couchpotato.lnk'; $s=$w.CreateShortcut($p); $s.TargetPath=$env:COUCHPOTATO_LAUNCHER; $s.WorkingDirectory=Split-Path $env:COUCHPOTATO_LAUNCHER; $s.Description='couchpotato'; $s.IconLocation=$env:COUCHPOTATO_ICON; $s.Save()`)
 ps.Env = append(os.Environ(), "COUCHPOTATO_LAUNCHER="+dst, "COUCHPOTATO_ICON="+filepath.Join(release,"mascot.ico"))
 ps.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
 // A managed PC may block shortcuts; this must not block the remote itself.
 if err := ps.Run(); err != nil { fmt.Println("Skrot w menu Start niedostepny. Uruchamiaj pobrany plik EXE.") }
 return nil
}

func main() {
 startup := len(os.Args)>1 && os.Args[1]=="--startup"
 kernel := syscall.NewLazyDLL("kernel32.dll")
 kernel.NewProc("SetConsoleOutputCP").Call(65001)
 if startup { window,_,_ := kernel.NewProc("GetConsoleWindow").Call(); syscall.NewLazyDLL("user32.dll").NewProc("ShowWindow").Call(window, 6) }
 title, _ := syscall.UTF16PtrFromString("couchpotato")
 kernel.NewProc("SetConsoleTitleW").Call(uintptr(unsafe.Pointer(title)))
 name, _ := syscall.UTF16PtrFromString("Local\\couchpotatoRemote")
 handle, _, lastErr := kernel.NewProc("CreateMutexW").Call(0, 0, uintptr(unsafe.Pointer(name)))
 if handle == 0 { fail(lastErr) }
 defer kernel.NewProc("CloseHandle").Call(handle)
 if lastErr == syscall.Errno(183) {
  fmt.Println("couchpotato juz dziala. Przed aktualizacja zamknij jego poprzednie okno.")
  url, _ := syscall.UTF16PtrFromString("http://127.0.0.1:8765")
  verb, _ := syscall.UTF16PtrFromString("open")
  syscall.NewLazyDLL("shell32.dll").NewProc("ShellExecuteW").Call(0, uintptr(unsafe.Pointer(verb)), uintptr(unsafe.Pointer(url)), 0, 0, 1)
  return
 }
 base := os.Getenv("LOCALAPPDATA"); if base == "" { fail(fmt.Errorf("brak folderu LOCALAPPDATA")) }
 root := filepath.Join(base, "couchpotato")
 fmt.Println("couchpotato — Edycja 27.10 20:30 — uruchamianie…")
 release, err := unpack(root); if err != nil { fail(err) }
 iconPath,_ := syscall.UTF16PtrFromString(filepath.Join(release,"mascot.ico"))
 user := syscall.NewLazyDLL("user32.dll")
 icon,_,_ := user.NewProc("LoadImageW").Call(0,uintptr(unsafe.Pointer(iconPath)),1,0,0,0x10|0x40)
 if icon != 0 { window,_,_ := kernel.NewProc("GetConsoleWindow").Call(); user.NewProc("SendMessageW").Call(window,0x80,0,icon); user.NewProc("SendMessageW").Call(window,0x80,1,icon) }
 if !startup { if err := installLauncher(root, release); err != nil { fail(err) } }
 cmd := exec.Command(filepath.Join(release, "runtime", "python.exe"), "-u", filepath.Join(release, "app.py"))
 cmd.Dir = release
 cmd.Env = append(os.Environ(), "PYTHONIOENCODING=utf-8")
 if startup { cmd.Env = append(cmd.Env, "COUCHPOTATO_STARTUP=1") }
 cmd.Stdin, cmd.Stdout, cmd.Stderr = os.Stdin, os.Stdout, os.Stderr
 if err := cmd.Run(); err != nil { fail(err) }
}
