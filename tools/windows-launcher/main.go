//go:build windows

// DragonGen.exe starts the Python game from the same folder.
package main

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"unsafe"
)

const createNoWindow = 0x08000000

func main() {
	if err := launch(); err != nil {
		showError(err.Error())
		os.Exit(1)
	}
}

func launch() error {
	executable, err := os.Executable()
	if err != nil {
		return fmt.Errorf("could not find the DragonGen folder: %w", err)
	}
	root := filepath.Dir(executable)
	script := filepath.Join(root, "main.py")
	if info, err := os.Stat(script); err != nil || !info.Mode().IsRegular() {
		return fmt.Errorf("main.py is missing. Extract the entire ZIP and keep DragonGen.exe beside main.py")
	}

	python, args, err := findPython(root)
	if err != nil {
		return err
	}

	var stderr bytes.Buffer
	game := exec.Command(python, append(args, script)...)
	game.Dir = root
	game.Stderr = &stderr
	game.SysProcAttr = &syscall.SysProcAttr{CreationFlags: createNoWindow}
	if err := game.Run(); err != nil {
		details := strings.TrimSpace(stderr.String())
		const maxDetails = 1600
		if len(details) > maxDetails {
			details = details[len(details)-maxDetails:]
		}
		if details == "" {
			details = err.Error()
		}
		return fmt.Errorf("DragonGen could not run. Check the Python and dependency setup in README.md.\n\n%s", details)
	}
	return nil
}

func findPython(root string) (string, []string, error) {
	for _, folder := range []string{".venv", "venv"} {
		path := filepath.Join(root, folder, "Scripts", "python.exe")
		if info, err := os.Stat(path); err == nil && info.Mode().IsRegular() {
			return path, nil, nil
		}
	}
	if path, err := exec.LookPath("python.exe"); err == nil {
		return path, nil, nil
	}
	if path, err := exec.LookPath("py.exe"); err == nil {
		return path, []string{"-3"}, nil
	}
	return "", nil, fmt.Errorf("Python 3 was not found. Install Python and the game dependencies as described in README.md")
}

func showError(message string) {
	title, _ := syscall.UTF16PtrFromString("DragonGen")
	// Drop embedded NULs so even malformed child-process output can be shown.
	body, _ := syscall.UTF16PtrFromString(strings.ReplaceAll(message, "\x00", ""))
	box := syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW")
	box.Call(0, uintptr(unsafe.Pointer(body)), uintptr(unsafe.Pointer(title)), 0x10)
}
