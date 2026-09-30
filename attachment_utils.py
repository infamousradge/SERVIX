from pathlib import Path
from PIL import Image, ImageOps
import shutil
import uuid, os, sys

APP_ROOT = Path(__file__).resolve().parent
if sys.platform == "win32":
    DATA_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home()/"AppData"/"Local"))/"SERVIX"
else:
    DATA_ROOT = Path.home()/".servix"
ATTACHMENTS = DATA_ROOT / "attachments"
ATTACHMENTS.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_PDF = {".pdf"}

def _safe_name(name: str) -> str:
    stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in Path(name).stem).strip() or "document"
    return stem[:80]

def store_attachment(source_path: str, service_code: str) -> dict:
    src = Path(source_path)
    ext = src.suffix.lower()
    if ext not in ALLOWED_IMAGE | ALLOWED_PDF:
        raise ValueError("Only image and PDF attachments are supported.")

    folder = ATTACHMENTS / service_code
    folder.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex[:10]
    original_size = src.stat().st_size

    if ext in ALLOWED_IMAGE:
        dest = folder / f"{_safe_name(src.name)}_{token}.jpg"
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "L"):
                bg = Image.new("RGB", im.size, "white")
                if "A" in im.getbands():
                    bg.paste(im, mask=im.getchannel("A"))
                    im = bg
                else:
                    im = im.convert("RGB")
            elif im.mode != "RGB":
                im = im.convert("RGB")
            im.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
            im.save(dest, "JPEG", quality=78, optimize=True, progressive=True)
        kind = "Image"
    else:
        # PDFs are copied losslessly in V1. We deliberately avoid destructive
        # PDF recompression that could make certificates/invoices unreadable.
        dest = folder / f"{_safe_name(src.name)}_{token}.pdf"
        shutil.copy2(src, dest)
        kind = "PDF"

    return {
        "original_name": src.name,
        "stored_path": str(dest),
        "kind": kind,
        "original_size": original_size,
        "stored_size": dest.stat().st_size,
    }
