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


def render_pdf(data, page=0):
    import pypdfium2 as pdfium

    with pdfium.PdfDocument(data) as document:
        source = document[page]
        try:
            width, height = source.get_size()
            if min(width, height) <= 0:
                raise ValueError("Invalid page dimensions")
            bitmap = source.render(scale=min(1200 / max(width, height), 4))
            try:
                image = bitmap.to_pil().convert("RGB")
            finally:
                bitmap.close()
        finally:
            source.close()
    try:
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()
    finally:
        image.close()


def read(data, suffix, page=0):
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")
    from PIL import Image
    import tesserocr

    if suffix == ".pdf":
        data = render_pdf(data, page)
    data = image_bytes(data)
    models = Path(__file__).resolve().parents[1] / "ocr_models"
    with Image.open(BytesIO(data)) as image:
        with tesserocr.PyTessBaseAPI(
            path=str(models), lang="fra+eng+deu", psm=tesserocr.PSM.AUTO
        ) as engine:
            engine.SetImage(image)
            return engine.GetUTF8Text()


if __name__ == "__main__":
    import sys

    sys.stdout.buffer.write(
        render_pdf(sys.stdin.buffer.read(10 * 1024 * 1024 + 1), int(sys.argv[1]))
    )
