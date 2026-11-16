"""Exercise the real isolated PDF reader, not a mocked extraction result."""

import io
import zlib

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from pypdf import PdfWriter

from eures_beta.employers.offer_ingestion import ImportFailure, read_pdf


def text_pdf(pages, *, compressed=False, with_action=False):
    """Build independent PDF 1.4 fixtures with WinAnsi text and exact xref offsets."""
    objects = [b'', b'']
    objects.append(
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>'
    )
    kids = []
    for text in pages:
        page_number = len(objects) + 1
        kids.append(f'{page_number} 0 R')
        content_number = page_number + 1
        objects.append(
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
            f'/Resources << /Font << /F1 3 0 R >> >> /Contents {content_number} 0 R >>'.encode()
        )
        literal = text.encode('cp1252').hex().encode()
        stream = b'BT /F1 12 Tf 40 780 Td <' + literal + b'> Tj ET'
        if compressed:
            stream = zlib.compress(stream)
        filters = b' /Filter /FlateDecode' if compressed else b''
        objects.append(
            b'<< /Length '
            + str(len(stream)).encode()
            + filters
            + b' >>\nstream\n'
            + stream
            + b'\nendstream'
        )
    action = (
        b' /OpenAction << /S /JavaScript /JS (app.alert\\("NOT_OFFER_CONTENT"\\);) >>'
        if with_action
        else b''
    )
    objects[0] = b'<< /Type /Catalog /Pages 2 0 R' + action + b' >>'
    objects[1] = (
        f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(pages)} >>'.encode()
    )
    output = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, value in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f'{index} 0 obj\n'.encode() + value + b'\nendobj\n')
    xref = len(output)
    output.extend(f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        output.extend(f'{offset:010} 00000 n \n'.encode())
    output.extend(
        f'trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    )
    return bytes(output)


class PdfCompatibilityTests(SimpleTestCase):
    def extract(self, data):
        return read_pdf(
            SimpleUploadedFile('fictional-offer.pdf', data),
            split_sections=False,
            include_text=True,
        )['_sourceText']

    def test_real_text_reader_preserves_languages_and_accents(self):
        texts = (
            'Électricien expérimenté : réparer les équipements et préparer les contrôles.',
            'Electrical technician: inspect equipment and maintain reliable production.',
            'Elektrotechniker: Geräte prüfen, Störungen beheben und Qualität sichern.',
        )
        for compressed in (False, True):
            for text in texts:
                with self.subTest(compressed=compressed, text=text):
                    self.assertIn(
                        text, self.extract(text_pdf([text], compressed=compressed))
                    )

    def test_compressed_multi_page_document_preserves_page_order(self):
        first = (
            'First page: maintain the electrical equipment and document every repair.'
        )
        second = 'Second page: inspect safety systems and support the maintenance team.'
        text = self.extract(text_pdf([first, second], compressed=True))
        self.assertLess(text.index(first), text.index(second))

    def test_pdf_actions_are_not_extracted_as_offer_text(self):
        content = (
            'Fictional offer: maintain machinery and inspect electrical equipment.'
        )
        text = self.extract(text_pdf([content], with_action=True))
        self.assertIn(content, text)
        self.assertNotIn('NOT_OFFER_CONTENT', text)

    def test_encrypted_document_is_refused(self):
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        writer.encrypt('fictional-password')
        output = io.BytesIO()
        writer.write(output)
        with self.assertRaises(ImportFailure):
            self.extract(output.getvalue())

    def test_page_limit_is_enforced_by_real_reader(self):
        with self.assertRaises(ImportFailure):
            self.extract(text_pdf(['Fictional maintenance technician offer.'] * 31))

    def test_malformed_pdf_is_refused(self):
        with self.assertRaises(ImportFailure):
            self.extract(b'%PDF-1.4\nnot a PDF object graph\n%%EOF\n')
