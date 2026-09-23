# -*- coding: utf-8 -*-
"""Shared geometry and labels for the PRISMA flow figure.

Single source of truth for the data, the palette, the type scale and the box
geometry. Both renderers import it, so the matplotlib PDF and the editable
draw.io file cannot drift apart:

    make_prisma_chart.py   -> figures/PRISMA.pdf / .svg / .tiff / .png
    make_prisma_drawio.py  -> figures/PRISMA.drawio

All labels are English and kept to PRISMA-standard wording; the Chinese
caption in the manuscript carries the translation for readers.

Coordinates are bottom-up (matplotlib convention): `y_top` is the distance from
the bottom of the canvas to the top edge of the element. The draw.io emitter
converts with `y = H - y_top`.

Figure contract
---------------
core conclusion : the review's statistical sample narrows from 252 candidate
                  records to 121 included studies through three documented
                  screening stages, and every exclusion is attributable.
archetype       : schematic-led composite, single panel, no data axes.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- design ----
FIG_WIDTH_MM = 89.0                 # single journal column
W = FIG_WIDTH_MM * 72.0 / 25.4      # 1 pt = 1 drawing unit
PAD_L, PAD_R, PAD_T, PAD_B = 6.0, 6.0, 7.0, 9.0
BAND_W, BAND_GAP = 13.0, 6.0
CONTENT_X = PAD_L + BAND_W + BAND_GAP          # 25.0
SPINE_X = CONTENT_X
SPINE_W = 118.0
EXCL_GAP = 6.0
EXCL_X = SPINE_X + SPINE_W + EXCL_GAP          # 149.0
EXCL_W = W - PAD_R - EXCL_X                    # ~97.3
SRC_GAP = 6.0
SRC_W = (W - PAD_R - CONTENT_X - SRC_GAP) / 2.0
SRC_H, SPINE_H = 46.0, 28.0
GAP_SRC, GAP_PLAIN = 16.0, 17.0

# exclusion block: header zone + one line per reason + bottom padding
SIDE_HEAD_ZONE, SIDE_ROW_H, SIDE_PAD_BOTTOM = 26.0, 9.0, 6.0
SIDE_HEAD_1, SIDE_HEAD_2, SIDE_ROW_1 = 7.0, 14.5, 23.0

C_INK = "#1B2733"
C_MUTED = "#5A6B7B"
C_ACCENT = "#1F4E8C"
C_ACCENT_SOFT = "#E8F0F9"
C_NEUTRAL_FILL = "#F6F9FC"
C_NEUTRAL_EDGE = "#B7C7D8"
C_SIDE_FILL = "#FBF7F1"
C_SIDE_EDGE = "#DFD2C0"
C_SIDE_INK = "#8A6B4F"
C_RULE = "#C3CEDA"
FONT = "Microsoft YaHei"

F_TITLE, F_COUNT = 7.0, 9.4
F_SRC, F_SRC_SUB = 6.6, 5.4
F_SIDE_HDR, F_SIDE = 6.4, 5.9
F_PHASE = 6.4

# ------------------------------------------------------------- evidence ----
DB = [("ACM DL", 63), ("IEEE", 52), ("Springer", 26), ("arXiv", 24),
      ("SciDirect", 21), ("USENIX", 17), ("PMLR/JMLR", 11)]
SNOW = [("Backward", 24), ("Forward", 14)]
DEDUP = [("Version merge", 11), ("Exact duplicates", 5), ("Not cited", 3)]
ABSTRACT = [("Weakly related", 20), ("Reviews and tutorials", 17),
            ("Documentation", 13), ("Ecosystem papers", 11)]
FULLTEXT = [("Outside compilation", 20), ("Outside energy", 13),
            ("Background only", 9), ("Not peer-reviewed", 9)]

BOXES = [
    # each box carries the exclusion performed on the way to the next box
    ("Records identified", 252,
     ("De-duplication", "n = 19 removed", DEDUP)),
    ("After de-duplication", 233,
     ("Abstract screening", "n = 61 removed", ABSTRACT)),
    ("After abstract screening", 172,
     ("Full-text screening", "n = 51 removed", FULLTEXT)),
    ("Included in the review", 121, None),
]

SOURCES = [
    ("Database search", 214,
     [" · ".join("{} {}".format(k, v) for k, v in DB[0:3]),
      " · ".join("{} {}".format(k, v) for k, v in DB[3:5]),
      " · ".join("{} {}".format(k, v) for k, v in DB[5:])]),
    ("Snowballing", 38,
     [" · ".join("{} {}".format(k, v) for k, v in SNOW)]),
]

BAND_LABELS = ["Identification", "Screening", "Included"]


def check_arithmetic():
    db, snow = sum(v for _, v in DB), sum(v for _, v in SNOW)
    assert db == 214 and snow == 38, (db, snow)
    assert sum(v for _, v in DEDUP) == 19
    assert sum(v for _, v in ABSTRACT) == 61
    assert sum(v for _, v in FULLTEXT) == 51
    assert db + snow == BOXES[0][1] == 252
    for i, (_, count, excl) in enumerate(BOXES[:-1]):
        assert excl is not None, "stage {} needs an exclusion block".format(i)
        assert count - int(excl[1].split("= ")[1].split()[0]) == BOXES[i + 1][1], (
            count, excl[1], BOXES[i + 1][1])
    assert BOXES[-1][1] == 121


def side_block_height(n_items):
    return SIDE_HEAD_ZONE + n_items * SIDE_ROW_H + SIDE_PAD_BOTTOM


def layout():
    """Return every element with its bottom-up geometry."""
    check_arithmetic()
    gaps = [max(GAP_PLAIN, side_block_height(len(excl[2])) + 10.0) if excl
            else GAP_PLAIN for _, _, excl in BOXES]
    H = (PAD_T + SRC_H + GAP_SRC
         + sum(SPINE_H + gaps[i] for i in range(len(BOXES) - 1))
         + SPINE_H + PAD_B)

    out = {"W": W, "H": H, "sources": [], "stages": [], "exclusions": [],
           "arrows": [], "connectors": [], "bands": [], "merge": None}

    y = H - PAD_T
    src_top = y
    for i, (title, total, lines) in enumerate(SOURCES):
        out["sources"].append({
            "x": CONTENT_X + i * (SRC_W + SRC_GAP), "y_top": src_top,
            "w": SRC_W, "h": SRC_H, "title": title, "total": total,
            "lines": lines})
    y = src_top - SRC_H

    centres = [s["x"] + s["w"] / 2.0 for s in out["sources"]]
    out["merge"] = {"centres": centres, "y_from": y, "y_mid": y - GAP_SRC / 2.0,
                    "y_to": y - GAP_SRC, "x": sum(centres) / len(centres)}
    y -= GAP_SRC

    spine_tops = []
    for idx, (title, count, excl) in enumerate(BOXES):
        spine_tops.append(y)
        out["stages"].append({
            "x": SPINE_X, "y_top": y, "w": SPINE_W, "h": SPINE_H,
            "title": title, "count": count, "last": idx == len(BOXES) - 1})
        y -= SPINE_H
        if idx < len(BOXES) - 1:
            gap = gaps[idx]
            out["arrows"].append({"x": SPINE_X + SPINE_W / 2.0,
                                  "y_from": y, "y_to": y - gap})
            if excl:
                bh = side_block_height(len(excl[2]))
                out["exclusions"].append({
                    "x": EXCL_X, "y_top": y - (gap - bh) / 2.0, "w": EXCL_W,
                    "h": bh, "header": excl[0], "subtotal": excl[1],
                    "items": excl[2]})
                out["connectors"].append({
                    "x0": SPINE_X + SPINE_W + 1.0, "x1": EXCL_X + 1.5,
                    "y": y - gap / 2.0})
            y -= gap

    out["bands"] = [
        {"x": PAD_L, "y_top": src_top,
         "h": src_top - (spine_tops[0] - SPINE_H), "label": BAND_LABELS[0]},
        {"x": PAD_L, "y_top": spine_tops[1],
         "h": spine_tops[1] - (spine_tops[2] - SPINE_H),
         "label": BAND_LABELS[1]},
        {"x": PAD_L, "y_top": spine_tops[3], "h": SPINE_H,
         "label": BAND_LABELS[2]},
    ]
    return out


def item_row_centres(exc):
    """Y centres of the exclusion rows, measured down from the block top."""
    return [SIDE_ROW_1 + j * SIDE_ROW_H for j in range(len(exc["items"]))]


if __name__ == "__main__":
    geom = layout()
    print("canvas {:.1f} x {:.1f} pt ({:.0f} mm wide, {:.0f} mm tall)".format(
        geom["W"], geom["H"], FIG_WIDTH_MM, geom["H"] / 72.0 * 25.4))
    print("arithmetic checks passed")
