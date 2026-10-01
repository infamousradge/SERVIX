"""Windows CI: check custom icon resources and real install/start/uninstall."""
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import subprocess
import time
import os
import sqlite3
import pefile
import ctypes
from ctypes import wintypes
import winreg
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parent


def capture_welcome(setup, dark):
    """Capture the real setup window in both themes on the disposable CI desktop."""
    theme_key = r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, theme_key) as key:
        try:
            old_value, old_type = winreg.QueryValueEx(key, 'AppsUseLightTheme')
        except FileNotFoundError:
            old_value, old_type = None, winreg.REG_DWORD
        winreg.SetValueEx(key, 'AppsUseLightTheme', 0, winreg.REG_DWORD, 0 if dark else 1)
        process = None
        try:
            process = subprocess.Popen([str(setup), '/NORESTART', '/SP-'])
            user32 = ctypes.windll.user32
            found = []
            callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def visit(hwnd, _):
                title = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, title, len(title))
                if user32.IsWindowVisible(hwnd) and title.value == 'SERVIX Setup':
                    found.append(hwnd)
                return True
            callback = callback_type(visit)
            for _ in range(40):
                found.clear()
                user32.EnumWindows(callback, 0)
                if found:
                    break
                time.sleep(0.25)
            assert found, 'Installer welcome window did not appear'
            hwnd = found[0]
            user32.SetForegroundWindow(hwnd)
            time.sleep(1)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            out = ROOT / 'installer-preview'
            out.mkdir(exist_ok=True)
            ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom)).save(
                out / ('setup-dark.png' if dark else 'setup-light.png'))
        finally:
            if process is not None and process.poll() is None:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               check=True, capture_output=True)
                process.wait(timeout=30)
            if old_value is None:
                winreg.DeleteValue(key, 'AppsUseLightTheme')
            else:
                winreg.SetValueEx(key, 'AppsUseLightTheme', 0, old_type, old_value)


def icon_payloads(path):
    data = path.read_bytes()
    count = struct.unpack_from('<H', data, 4)[0]
    entries = [struct.unpack_from('<BBBBHHII', data, 6+i*16) for i in range(count)]
    return {data[entry[-1]:entry[-1]+entry[-2]] for entry in entries}


def verify_icon(exe, expected):
    with pefile.PE(str(exe)) as pe:
        icons = []
        for resource in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            if resource.id == pefile.RESOURCE_TYPE['RT_ICON']:
                for icon in resource.directory.entries:
                    for language in icon.directory.entries:
                        item = language.data.struct
                        icons.append(pe.get_data(item.OffsetToData, item.Size))
        assert expected.issubset(set(icons)), f'Custom SERVIX icon sizes missing from {exe}'


def main():
    setup = ROOT / 'installer-output' / 'SERVIX-Setup.exe'
    expected = icon_payloads(ROOT / 'assets' / 'servix.ico')
    verify_icon(setup, expected)
    verify_icon(ROOT / 'dist' / 'SERVIX' / 'SERVIX.exe', expected)
    installer_script=(ROOT/'installer'/'SERVIX.iss').read_text(encoding='utf-8')
    assert 'SERVIX Demo Workspace' in installer_script and 'Parameters: "--demo"' in installer_script, 'Demo Workspace Start menu shortcut missing'
    capture_welcome(setup, dark=False)
    capture_welcome(setup, dark=True)
    with TemporaryDirectory(prefix='servix-installed-') as folder:
        target = Path(folder) / 'SERVIX'
        subprocess.run([str(setup), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                        '/NOICONS', '/MERGETASKS=!desktopicon', f'/DIR={target}'],
                       check=True, timeout=180)
        installed = target / 'SERVIX.exe'
        assert installed.exists(), 'Installed executable missing'
        assert (target / '_internal' / 'assets' / 'logo.png').read_bytes() == (ROOT / 'assets' / 'logo.png').read_bytes()
        verify_icon(installed, expected)
        process = subprocess.Popen([str(installed)])
        try:
            time.sleep(8)
            assert process.poll() is None, f'Installed SERVIX exited with {process.returncode}'
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=30)
        demo_process = subprocess.Popen([str(installed), '--demo'])
        try:
            time.sleep(8)
            assert demo_process.poll() is None, f'Demo Workspace exited with {demo_process.returncode}'
            local = Path(os.environ['LOCALAPPDATA'])
            demo_db = local / 'SERVIX Demo Workspace' / 'data' / 'servix.db'
            live_db = local / 'SERVIX' / 'data' / 'servix.db'
            assert demo_db.exists(), 'Demo Workspace database missing'
            assert not demo_db.samefile(live_db), 'Demo Workspace points to the live database'
            with sqlite3.connect(demo_db) as con:
                assert con.execute("SELECT COUNT(*) FROM clients WHERE code LIKE 'CLI-DEMO-%'").fetchone()[0] == 2
                assert con.execute("SELECT COUNT(*) FROM history h JOIN services s ON s.id=h.service_id WHERE s.code='SRV-DEMO-0001'").fetchone()[0] >= 3
        finally:
            if demo_process.poll() is None:
                demo_process.terminate()
            demo_process.wait(timeout=30)
        subprocess.run([str(target / 'unins000.exe'), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'],
                       check=True, timeout=180)
        assert not installed.exists(), 'Uninstall did not remove executable'
    print('Custom icons, exact logo, install, app startup, isolated demo data, and uninstall passed')


if __name__ == '__main__':
    main()
