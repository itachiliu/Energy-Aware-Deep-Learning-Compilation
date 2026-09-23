# -*- coding: utf-8 -*-
"""Trim the blank margins of an exported figure PDF.

draw.io exports the whole diagram page, background rectangle included, so the
drawing often sits inside wide blank margins. LaTeX then scales the *page* to
the column width and the visible diagram ends up small. This script recomputes
the content bounding box (ignoring page-filling background rectangles) and
moves the PDF page boundary onto it, leaving a small uniform margin.

    python figures/trim_pdf_margins.py in.pdf out.pdf [--margin 4]
"""
import sys
from pathlib import Path

import pymupdf


def content_rect(page, margin):
    pw, ph = page.rect.width, page.rect.height
    boxes = []
    for drawing in page.get_drawings():
        r = drawing["rect"]
        if r.width >= pw * 0.98 and r.height >= ph * 0.98:
            continue                      # page-filling background rectangle
        boxes.append(r)
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if span["text"].strip():
                    boxes.append(pymupdf.Rect(span["bbox"]))
    if not boxes:
        return page.rect
    x0 = min(b.x0 for b in boxes)
    y0 = min(b.y0 for b in boxes)
    x1 = max(b.x1 for b in boxes)
    y1 = max(b.y1 for b in boxes)
    rect = pymupdf.Rect(x0 - margin, y0 - margin, x1 + margin, y1 + margin)
    return rect & page.rect


def main():
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    margin = 4.0
    if "--margin" in sys.argv:
        margin = float(sys.argv[sys.argv.index("--margin") + 1])

    doc = pymupdf.open(src)
    for page in doc:
        before = page.rect
        rect = content_rect(page, margin)
        page.set_cropbox(rect)
        page.set_mediabox(rect)
        print("page {:.1f} x {:.1f} -> {:.1f} x {:.1f} pt".format(
            before.width, before.height, rect.width, rect.height))
    doc.save(dst)
    print("saved {}".format(dst))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
