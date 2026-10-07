from pathlib import Path
from shutil import copyfile
from urllib.request import urlretrieve
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

APP_EXACT = ASSETS / "app-icon-exact.png"
SIDEBAR_EXACT = ASSETS / "sidebar-logo-exact.png"
LOGIN_EXACT = ASSETS / "login-mark-exact.png"

ICON = ASSETS / "app-icon-generated.png"
SIDEBAR = ASSETS / "logo-transparent.png"
LOGIN_MARK = ASSETS / "login-mark-generated.png"
MANROPE = ASSETS / "Manrope-wght.ttf"
MANROPE_LICENSE = ASSETS / "Manrope-OFL.txt"

for source in (APP_EXACT, SIDEBAR_EXACT, LOGIN_EXACT):
    if not source.exists():
        raise SystemExit(f"Locked SERVIX asset not found: {source}")

# Verify the locked PNGs before using them so a damaged repository asset can
# never silently reach the installer.
for source in (APP_EXACT, SIDEBAR_EXACT, LOGIN_EXACT):
    with Image.open(source) as img:
        img.verify()

# Copy the supplied artwork exactly; no crop, recolour or generated substitute.
copyfile(APP_EXACT, ICON)
copyfile(SIDEBAR_EXACT, SIDEBAR)
copyfile(LOGIN_EXACT, LOGIN_MARK)

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
