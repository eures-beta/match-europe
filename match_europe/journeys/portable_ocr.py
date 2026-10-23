"""Local Tesseract fallback with bundled FR/EN/DE models; no network access."""

import os
from io import BytesIO
from pathlib import Path


def image_bytes(data):
    """Bound raster input before either the native or command-line OCR engine."""
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = 20_000_000
    with Image.open(BytesIO(data)) as source:
        if source.width * source.height > Image.MAX_IMAGE_PIXELS:
            raise ValueError("Oversized image")
        source.thumbnail((900, 1200))
        result = BytesIO()
        source.convert("RGB").save(result, format="PNG")
        return result.getvalue()


def read(data, suffix, page=0):
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")
    from PIL import Image
    import tesserocr

    Image.MAX_IMAGE_PIXELS = 20_000_000
    models = Path(__file__).resolve().parents[1] / "ocr_models"
    if suffix == ".pdf":
        import pypdfium2 as pdfium

        with pdfium.PdfDocument(data) as document:
            source = document[page]
            try:
                width, height = source.get_size()
                if min(width, height) <= 0:
                    raise ValueError("Invalid page dimensions")
                # Match the system renderer limit; never allocate a full-size large page.
                scale = min(1200 / max(width, height), 4)
                bitmap = source.render(scale=scale)
                try:
                    image = bitmap.to_pil().convert("RGB")
                finally:
                    bitmap.close()
            finally:
                source.close()
    else:
        with Image.open(BytesIO(data)) as source:
            if source.width * source.height > Image.MAX_IMAGE_PIXELS:
                raise ValueError("Oversized image")
            source.thumbnail((900, 1200))
            image = source.convert("RGB")
    try:
        with tesserocr.PyTessBaseAPI(
            path=str(models), lang="fra+eng+deu", psm=tesserocr.PSM.AUTO
        ) as engine:
            engine.SetImage(image)
            return engine.GetUTF8Text()
    finally:
        image.close()
