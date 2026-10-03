"""Prepare Windows icon sizes and DPI-ready installer branding assets."""
from pathlib import Path
import os
from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent / 'assets'
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def ui_font(size, bold=False):
    name = 'segoeuib.ttf' if bold else 'segoeui.ttf'
    candidates = [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / name]
    if os.environ.get('SERVIX_BRANDING_FONT_DIR'):
        candidates.append(Path(os.environ['SERVIX_BRANDING_FONT_DIR']) /
                          ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'))
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def build_assets():
    mark = Image.open(ASSETS / 'servix-mark.png').convert('RGBA')
    mark.save(ASSETS / 'servix.ico', sizes=[(s, s) for s in ICON_SIZES])
    logo = Image.open(ASSETS / 'logo.png').convert('RGBA')
    for dark in (False, True):
        # Inno preserves the 164:314 aspect ratio; this is a 4x raster for high DPI.
        width, height = 656, 1256
        canvas = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(canvas)
        top = (7, 26, 61) if dark else (8, 44, 82)
        bottom = (6, 70, 101) if dark else (8, 106, 161)
        for y in range(height):
            ratio = y / (height - 1)
            color = tuple(round(a + (b-a)*ratio) for a, b in zip(top, bottom))
            draw.line((0, y, width, y), fill=color)
        draw.rounded_rectangle((42, 130, 614, 700), radius=32, fill='#FFFFFF')
        fitted = logo.copy()
        fitted.thumbnail((532, 530), Image.Resampling.LANCZOS)
        canvas.paste(fitted, ((width-fitted.width)//2, 150+(530-fitted.height)//2), fitted)
        draw.text((54, 760), 'Your service', font=ui_font(43, True), fill='white')
        draw.text((54, 814), 'workspace.', font=ui_font(43, True), fill='white')
        draw.rounded_rectangle((54, 904, 160, 914), radius=5, fill='#22C4CB')
        for index, label in enumerate(('Service', 'Calibration', 'AMC management')):
            draw.text((54, 952+index*52), label, font=ui_font(29), fill='#DCEEFF')
        canvas.save(ASSETS / ('installer-dark.png' if dark else 'installer-light.png'), optimize=True)
    small = Image.new('RGBA', (128, 128))
    fitted = mark.copy()
    fitted.thumbnail((116, 116), Image.Resampling.LANCZOS)
    small.paste(fitted, ((128-fitted.width)//2, (128-fitted.height)//2), fitted)
    small.save(ASSETS / 'installer-small.png', optimize=True)
    icon = Image.open(ASSETS / 'servix.ico')
    assert icon.ico.sizes() == {(s, s) for s in ICON_SIZES}
    print('SERVIX icon and installer branding prepared')


if __name__ == '__main__':
    build_assets()
