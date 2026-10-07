from base64 import b64decode
from pathlib import Path
from shutil import copyfile
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

APP_B64 = ASSETS / "servix-app-icon.b64.txt"
SIDEBAR_B64 = ASSETS / "servix-sidebar-logo.b64.txt"
ICON = ASSETS / "app-icon-generated.png"
SIDEBAR = ASSETS / "logo-transparent.png"
LOGIN_MARK = ASSETS / "login-mark-generated.png"
MANROPE = ASSETS / "Manrope-wght.ttf"
MANROPE_LICENSE = ASSETS / "Manrope-OFL.txt"

def decode_asset(source: Path, target: Path) -> None:
    if not source.exists():
        raise SystemExit(f"Locked SERVIX asset source not found: {source}")
    raw = "".join(source.read_text(encoding="utf-8").split())
    target.write_bytes(b64decode(raw))

# Use the exact locked images supplied for this build. No cropping, recolouring
# or generated approximation is applied to the Windows icon or sidebar logo.
decode_asset(APP_B64, ICON)
decode_asset(SIDEBAR_B64, SIDEBAR)

# The compact login uses the same exact emblem source, preserving transparency
# and proportions rather than reusing/cropping the sidebar wordmark.
copyfile(ICON, LOGIN_MARK)

# Bundle Manrope so SERVIX keeps identical typography while fully offline.
if not MANROPE.exists():
    urlretrieve(
        "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/Manrope%5Bwght%5D.ttf",
        MANROPE,
    )
if not MANROPE_LICENSE.exists():
    urlretrieve(
        "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/OFL.txt",
        MANROPE_LICENSE,
    )

print(f"Prepared exact SERVIX app icon: {ICON}")
print(f"Prepared exact SERVIX sidebar logo: {SIDEBAR}")
print(f"Prepared SERVIX login mark: {LOGIN_MARK}")
print(f"Prepared bundled Manrope font: {MANROPE}")
