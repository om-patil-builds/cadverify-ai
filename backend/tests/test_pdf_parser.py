import tempfile
import unittest
from pathlib import Path

import fitz

from app.services.pdf_parser import parse_pdf


class TestPdfParser(unittest.TestCase):
    def test_parse_pdf_extracts_metadata_and_text_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Hello CADVerify AI")
            page.insert_text((72, 120), "Second line of text")
            doc.set_metadata(
                {
                    "title": "Sample PDF",
                    "author": "Test Author",
                    "creator": "PyMuPDF",
                    "producer": "pdf-parser-test",
                    "creationDate": "20250101000000Z",
                }
            )
            doc.save(str(path))

            result = parse_pdf(str(path))

            self.assertEqual(result["page_count"], 1)
            self.assertEqual(result["metadata"]["title"], "Sample PDF")
            self.assertEqual(result["metadata"]["author"], "Test Author")
            self.assertGreaterEqual(result["text_block_count"], 1)
            self.assertGreaterEqual(result["total_text_count"], 3)
            self.assertIsInstance(result["text_blocks"], list)


if __name__ == "__main__":
    unittest.main()
