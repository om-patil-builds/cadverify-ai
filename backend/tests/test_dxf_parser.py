import tempfile
import unittest
from pathlib import Path

import ezdxf

from app.services.dxf_parser import parse_dxf


class TestDxfParser(unittest.TestCase):
    def test_parse_dxf_extracts_basic_entities(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.dxf"
            doc = ezdxf.new("R2010")
            msp = doc.modelspace()
            msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "0"})
            msp.add_circle((5, 0), 2, dxfattribs={"layer": "DIM"})
            msp.add_text("HELLO", dxfattribs={"insert": (1, 1), "height": 2.5, "layer": "TEXT"})
            doc.saveas(path)

            result = parse_dxf(str(path))

            self.assertEqual(result["summary"]["lines"], 1)
            self.assertEqual(result["summary"]["circles"], 1)
            self.assertEqual(result["summary"]["texts"], 1)
            self.assertEqual(len(result["entities"]["lines"]), 1)
            self.assertEqual(len(result["entities"]["circles"]), 1)
            self.assertEqual(len(result["entities"]["texts"]), 1)


if __name__ == "__main__":
    unittest.main()
