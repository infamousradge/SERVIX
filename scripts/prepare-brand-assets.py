from collections import deque
from pathlib import Path
from urllib.request import urlretrieve
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SOURCE = ASSETS / "logo.png"
TRANSPARENT = ASSETS / "logo-transparent.png"
ICON = ASSETS / "app-icon-generated.png"
MANROPE = ASSETS / "Manrope-wght.ttf"
MANROPE_LICENSE = ASSETS / "Manrope-OFL.txt"

if not SOURCE.exists():
    raise SystemExit(f"SERVIX source logo not found: {SOURCE}")

# Bundle Manrope so SERVIX keeps the same typography even while fully offline.
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

img = Image.open(SOURCE).convert("RGBA")
w, h = img.size
px = img.load()
visited = bytearray(w * h)
queue: deque[tuple[int, int]] = deque()


def is_background(x: int, y: int) -> bool:
    r, g, b, a = px[x, y]
    mx, mn = max(r, g, b), min(r, g, b)
    return a > 0 and mn >= 232 and (mx - mn) <= 24


def seed(x: int, y: int) -> None:
    idx = y * w + x
    if not visited[idx] and is_background(x, y):
        visited[idx] = 1
        queue.append((x, y))


# Remove only the connected near-white exterior so the original SERVIX artwork
# is preserved while the surrounding white canvas becomes transparent.
for x in range(w):
    seed(x, 0)
    seed(x, h - 1)
for y in range(h):
    seed(0, y)
    seed(w - 1, y)

while queue:
    x, y = queue.popleft()
    r, g, b, _ = px[x, y]
    px[x, y] = (r, g, b, 0)
    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if 0 <= nx < w and 0 <= ny < h:
            idx = ny * w + nx
            if not visited[idx] and is_background(nx, ny):
                visited[idx] = 1
                queue.append((nx, ny))

# The old SERVIX sidebar artwork used a white SERVIX wordmark/tagline on the
# dark navy shell while retaining the original cyan/green X. Recreate that
# treatment from the locked original logo instead of using a white rectangle.
sidebar = img.copy()
spx = sidebar.load()
wordmark_top = int(h * 0.70)
tagline_top = int(h * 0.89)
x_start = int(w * 0.715)
for y in range(wordmark_top, h):
    for x in range(w):
        r, g, b, a = spx[x, y]
        if a == 0:
            continue
        if y >= tagline_top:
            # Soft white tagline, matching the old dark-sidebar treatment.
            spx[x, y] = (232, 243, 252, a)
        elif x < x_start:
            # SERVI becomes white; the colourful X stays untouched.
            spx[x, y] = (247, 251, 255, a)

sidebar.save(TRANSPARENT, "PNG", optimize=True)

# Generate the Windows icon from the actual emblem bounds in the original
# artwork. This avoids the previous loose crop that made the installed icon
# look different from the old SERVIX mark.
alpha = img.getchannel("A")
upper = alpha.crop((0, 0, w, int(h * 0.705)))
bbox = upper.getbbox()
if not bbox:
    raise SystemExit("Unable to locate SERVIX emblem in source logo")
left, top, right, bottom = bbox
pad_x = max(6, int((right - left) * 0.025))
pad_y = max(6, int((bottom - top) * 0.025))
left = max(0, left - pad_x)
top = max(0, top - pad_y)
right = min(w, right + pad_x)
bottom = min(int(h * 0.715), bottom + pad_y)
emblem = img.crop((left, top, right, bottom))

canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
padding = 54
available = 1024 - padding * 2
ratio = min(available / emblem.width, available / emblem.height)
size = (max(1, round(emblem.width * ratio)), max(1, round(emblem.height * ratio)))
emblem = emblem.resize(size, Image.Resampling.LANCZOS)
canvas.alpha_composite(emblem, ((1024 - size[0]) // 2, (1024 - size[1]) // 2))
canvas.save(ICON, "PNG", optimize=True)

print(f"Prepared SERVIX dark-shell logo: {TRANSPARENT}")
print(f"Prepared SERVIX Windows emblem icon: {ICON}")
print(f"Prepared bundled Manrope font: {MANROPE}")
