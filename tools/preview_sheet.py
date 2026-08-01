"""Build an 8x nearest-neighbor preview sheet from raw 256px Q renders."""
import json
import sys
from pathlib import Path

from PIL import Image

root = Path(sys.argv[1])
out = Path(sys.argv[2])
directions = ("front", "right", "back", "left")
cells = []
for d in directions:
    for f in range(8):
        p = root / d / ("frame_%02d" % f) / "beauty.png"
        if not p.is_file():
            raise SystemExit("missing %s" % p)
        cells.append(Image.open(p).convert("RGBA"))
w, h = cells[0].size
sheet = Image.new("RGBA", (w * 8, h * len(directions)), (0, 0, 0, 0))
for i, img in enumerate(cells):
    sheet.paste(img, ((i % 8) * w, (i // 8) * h))
sheet = sheet.resize((w * 8 * 8, h * len(directions) * 8), Image.NEAREST)
sheet.save(out)
print("preview saved:", out)
