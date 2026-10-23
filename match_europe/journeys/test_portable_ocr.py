"""Actual image/scanned PDF recognition when system binaries are absent."""

from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image, ImageDraw, ImageFont

from .offer_ingestion import read_pdf


class PortableOCRTests(SimpleTestCase):
    def document(self, format):
        image = Image.new("RGB", (1600, 600), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=42)
        draw.multiline_text(
            (60, 60),
            "Fictional technician\nCompany: Fictional employer\nWorkplace: Metz\nTasks: Repair equipment.\nSkills: Technical training.",
            fill="black",
            font=font,
            spacing=25,
        )
        data = BytesIO()
        image.save(data, format=format)
        image.close()
        return data.getvalue()

    @patch.dict("os.environ", {"PATH": ""})
    def test_image_without_tesseract_executable(self):
        result = read_pdf(SimpleUploadedFile("fictional.png", self.document("PNG")))
        self.assertEqual(result["extraction"], "document_ocr")
        self.assertIn("technician", result["title"].lower())
        self.assertTrue(
            any(warning["field"] == "ocr" for warning in result["extractionWarnings"])
        )

    @patch.dict("os.environ", {"PATH": ""})
    def test_scanned_pdf_without_poppler_or_tesseract_executables(self):
        result = read_pdf(SimpleUploadedFile("fictional.pdf", self.document("PDF")))
        self.assertEqual(result["extraction"], "document_ocr")
        self.assertIn("technician", result["title"].lower())
