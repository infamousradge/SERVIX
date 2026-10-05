from collections import deque
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "logo.png"
TRANSPARENT = ROOT / "assets" / "logo-transparent.png"
ICON = ROOT / "assets" / "app-icon-generated.png"

if not SOURCE.exists():
    raise SystemExit(f"SERVIX source logo not found: {SOURCE}")

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

img.save(TRANSPARENT, "PNG", optimize=True)

# Use only the emblem from the exact approved SERVIX artwork for the installed app icon.
left = int(w * 0.08)
top = int(h * 0.02)
right = int(w * 0.92)
bottom = int(h * 0.73)
emblem = img.crop((left, top, right, bottom))

canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
padding = 66
available = 1024 - padding * 2
ratio = min(available / emblem.width, available / emblem.height)
size = (max(1, round(emblem.width * ratio)), max(1, round(emblem.height * ratio)))
emblem = emblem.resize(size, Image.Resampling.LANCZOS)
canvas.alpha_composite(emblem, ((1024 - size[0]) // 2, (1024 - size[1]) // 2))
canvas.save(ICON, "PNG", optimize=True)

print(f"Prepared SERVIX transparent logo: {TRANSPARENT}")
print(f"Prepared SERVIX Windows icon: {ICON}")
