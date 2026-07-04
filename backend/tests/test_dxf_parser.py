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

    def test_parse_dxf_extracts_all_supported_entities(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample_full.dxf"
            doc = ezdxf.new("R2010")
            msp = doc.modelspace()
            msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "LINES"})
            msp.add_circle((5, 0), 2, dxfattribs={"layer": "CIRCLES"})
            msp.add_arc((5, 0), 3, 0, 180, dxfattribs={"layer": "ARCS"})
            msp.add_lwpolyline([(0, 0), (5, 5), (10, 0)], dxfattribs={"layer": "POLYS"})
            msp.add_text("SAMPLE", dxfattribs={"insert": (1, 1), "height": 2.5, "layer": "TEXTS"})
            msp.add_mtext("Multi-line text", dxfattribs={"insert": (2, 2), "char_height": 1.0, "layer": "TEXTS"})
            doc.saveas(path)

            result = parse_dxf(str(path))

            self.assertEqual(result["summary"]["lines"], 1)
            self.assertEqual(result["summary"]["circles"], 1)
            self.assertEqual(result["summary"]["arcs"], 1)
            self.assertEqual(result["summary"]["polylines"], 1)
            self.assertEqual(result["summary"]["texts"], 2)
            self.assertEqual(len(result["entities"]["lines"]), 1)
            self.assertEqual(len(result["entities"]["circles"]), 1)
            self.assertEqual(len(result["entities"]["arcs"]), 1)
            self.assertEqual(len(result["entities"]["polylines"]), 1)
            self.assertEqual(len(result["entities"]["texts"]), 2)


if __name__ == "__main__":
    unittest.main()
