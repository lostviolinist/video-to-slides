from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from vts.frames import deduplicate_frames


class FrameTests(unittest.TestCase):
    def test_color_and_perceptual_hashes_preserve_distinct_scenes(self) -> None:
        try:
            from PIL import Image
            import imagehash  # noqa: F401
        except ImportError:
            self.skipTest("frame-analysis dependencies are not installed")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            red = root / "red.jpg"
            red_copy = root / "red-copy.jpg"
            blue = root / "blue.jpg"
            Image.new("RGB", (320, 180), "red").save(red)
            Image.new("RGB", (320, 180), "red").save(red_copy)
            Image.new("RGB", (320, 180), "blue").save(blue)
            frames = deduplicate_frames(
                [
                    {"timestamp": 0, "signal": "heartbeat", "path": str(red)},
                    {"timestamp": 1, "signal": "scene-change", "path": str(red_copy)},
                    {"timestamp": 2, "signal": "scene-change", "path": str(blue)},
                ],
                sharpness_floor=0,
            )
        self.assertEqual(len(frames), 2)
        self.assertEqual({Path(frame["path"]).name for frame in frames}, {"red-copy.jpg", "blue.jpg"})


if __name__ == "__main__":
    unittest.main()
