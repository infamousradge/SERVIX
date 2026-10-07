from base64 import b64decode
from pathlib import Path
from shutil import copyfile
from urllib.request import urlretrieve
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

APP_EXACT = ASSETS / "app-icon-exact.png"
LOGIN_EXACT = ASSETS / "login-mark-exact.png"

ICON = ASSETS / "app-icon-generated.png"
SIDEBAR = ASSETS / "logo-transparent.png"
LOGIN_MARK = ASSETS / "login-mark-generated.png"
MANROPE = ASSETS / "Manrope-wght.ttf"
MANROPE_LICENSE = ASSETS / "Manrope-OFL.txt"

for source in (APP_EXACT, LOGIN_EXACT):
    if not source.exists():
        raise SystemExit(f"Locked SERVIX asset not found: {source}")

sidebar_parts = [ASSETS / f"sidebar-exact-{i:02d}.b64part" for i in range(12)]
for source in sidebar_parts:
    if not source.exists():
        raise SystemExit(f"Locked SERVIX sidebar part not found: {source}")

# Use the supplied app icon and login emblem exactly.
copyfile(APP_EXACT, ICON)
copyfile(LOGIN_EXACT, LOGIN_MARK)

# The exact sidebar PNG is stored as bounded base64 chunks so GitHub transfer
# cannot truncate the original binary. Reassemble it byte-for-byte at build time.
sidebar_b64 = "".join(p.read_text(encoding="utf-8") for p in sidebar_parts)
SIDEBAR.write_bytes(b64decode(sidebar_b64))

# Validate all three PNGs before Tauri packages them.
for source in (ICON, SIDEBAR, LOGIN_MARK):
    with Image.open(source) as img:
        img.verify()

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
print(f"Prepared exact SERVIX login mark: {LOGIN_MARK}")
print(f"Prepared bundled Manrope font: {MANROPE}")
