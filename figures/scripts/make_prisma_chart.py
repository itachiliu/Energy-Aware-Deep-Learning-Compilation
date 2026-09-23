# -*- coding: utf-8 -*-
"""Render figures/PRISMA.pdf from the shared layout in prisma_layout.py.

Figure contract
---------------
core conclusion : the review's statistical sample narrows from 252 candidate
                  records to 121 included studies through three documented
                  screening stages, and every exclusion is attributable.
scientific role : methods / provenance figure (no data axes).
archetype       : schematic-led composite, single panel.
evidence chain  : identification 214 + 38 = 252
                  -> dedup & version merge -19 -> 233
                  -> title/abstract screening -61 -> 172
                  -> full-text eligibility -51 -> 121 -> included.
backend         : Python / matplotlib (exclusive for drawing and export).
export contract : 89 mm column width, 1 pt = 1 drawing unit, vector PDF with
                  editable text (pdf.fonttype 42), no glyph below 5 pt.
qa              : scripts/validate_figure.py, scripts/audit_pdf_text.py,
                  scripts/audit_figure_collisions.py.

Run:  python figures/make_prisma_chart.py
"""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle
from matplotlib.textpath import TextPath

from prisma_layout import (
    BAND_W, C_ACCENT, C_ACCENT_SOFT, C_INK, C_MUTED, C_NEUTRAL_EDGE,
    C_NEUTRAL_FILL, C_RULE, C_SIDE_EDGE, C_SIDE_FILL, C_SIDE_INK, FONT,
    FIG_WIDTH_MM, F_COUNT, F_PHASE, F_SIDE, F_SIDE_HDR, F_SRC, F_SRC_SUB,
    F_TITLE, HERE, SIDE_HEAD_1, SIDE_HEAD_2, SIDE_ROW_1, SIDE_ROW_H, layout,
)

OUT_PDF = HERE / "PRISMA.pdf"
OUT_SVG = HERE / "PRISMA.svg"
OUT_PNG = HERE / "PRISMA.png"
OUT_TIFF = HERE / "PRISMA.tiff"

# export contract: width_mm = 89.0 (one journal column); enforced in main()
COLUMN_WIDTH_MM = 89.0

_PROP = FontProperties(family=FONT)


def text_w(s, size):
    """Rendered width of `s` in points at `size`."""
    if not s:
        return 0.0
    return TextPath((0, 0), s, size=size, prop=_PROP).get_extents().width


def fit(s, size, limit, what):
    w = text_w(s, size)
    assert w <= limit, "{}: '{}' needs {:.1f}pt > {:.1f}pt".format(
        what, s, w, limit)
    return w


def rounded(ax, x, y, w, h, fc, ec, lw=0.8, r=3.0, z=2):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0,rounding_size={}".format(r),
        linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z,
        mutation_aspect=1.0))


def arrow_down(ax, x, y_from, y_to, color=C_NEUTRAL_EDGE, lw=1.0, head=4.2):
    """Vertical arrow with a solid triangular head, pointing downwards."""
    ax.plot([x, x], [y_from, y_to + head], color=color, lw=lw, zorder=1,
            solid_capstyle="butt")
    ax.add_patch(Polygon([[x, y_to], [x - head * 0.42, y_to + head],
                          [x + head * 0.42, y_to + head]],
                         closed=True, facecolor=color, edgecolor="none",
                         zorder=1))


def item_line(ax, x_left, x_right, yc, reason, n, size):
    ax.text(x_left, yc, reason, fontsize=size, color=C_INK, ha="left",
            va="center", zorder=4)
    ax.text(x_right, yc, str(n), fontsize=size, color=C_SIDE_INK, ha="right",
            va="center", weight="bold", zorder=4)


def main():
    geom = layout()
    W, H = geom["W"], geom["H"]
    assert abs(W - COLUMN_WIDTH_MM * 72.0 / 25.4) < 1e-9, (
        "figure width no longer matches the {:.1f} mm column contract".format(
            COLUMN_WIDTH_MM))
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [FONT, "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 7.0,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })

    fig = plt.figure(figsize=(W / 72.0, H / 72.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # --- identification: two source boxes side by side ---------------------
    for src in geom["sources"]:
        x, top, w, h = src["x"], src["y_top"], src["w"], src["h"]
        rounded(ax, x, top - h, w, h, C_NEUTRAL_FILL, C_NEUTRAL_EDGE)
        head = "{}  n = {}".format(src["title"], src["total"])
        fit(head, F_SRC, w - 10, "source head")
        n_lines = len(src["lines"])
        block = F_SRC + 4.0 + n_lines * 6.2
        head_centre = top - (h - block) / 2.0 - F_SRC / 2.0
        ax.text(x + w / 2.0, head_centre, head, fontsize=F_SRC,
                color=C_ACCENT, ha="center", va="center", weight="bold",
                zorder=4)
        for j, line in enumerate(src["lines"]):
            fit(line, F_SRC_SUB, w - 10, "source detail")
            ax.text(x + w / 2.0, head_centre - F_SRC / 2.0 - 4.0 - 3.1
                    - j * 6.2, line,
                    fontsize=F_SRC_SUB, color=C_MUTED, ha="center",
                    va="center", zorder=4)

    merge = geom["merge"]
    for cx in merge["centres"]:
        ax.plot([cx, cx], [merge["y_from"], merge["y_mid"]],
                color=C_NEUTRAL_EDGE, lw=1.0, zorder=1)
    ax.plot(merge["centres"], [merge["y_mid"], merge["y_mid"]],
            color=C_NEUTRAL_EDGE, lw=1.0, zorder=1)
    arrow_down(ax, merge["x"], merge["y_mid"], merge["y_to"])

    # --- exclusion blocks and their connectors ----------------------------
    for conn in geom["connectors"]:
        ax.plot([conn["x0"], conn["x1"]], [conn["y"], conn["y"]],
                color=C_RULE, lw=0.8, zorder=1)
    for exc in geom["exclusions"]:
        x, top, w, h = exc["x"], exc["y_top"], exc["w"], exc["h"]
        rounded(ax, x, top - h, w, h, C_SIDE_FILL, C_SIDE_EDGE)
        fit(exc["header"], F_SIDE_HDR, w - 10, "exclusion header")
        fit(exc["subtotal"], F_SIDE_HDR, w - 10, "exclusion subtotal")
        ax.text(x + 5.0, top - SIDE_HEAD_1, exc["header"],
                fontsize=F_SIDE_HDR,
                color=C_SIDE_INK, ha="left", va="center", weight="bold",
                zorder=4)
        ax.text(x + 5.0, top - SIDE_HEAD_2, exc["subtotal"],
                fontsize=F_SIDE, color=C_MUTED, ha="left", va="center",
                zorder=4)
        for j, (reason, n) in enumerate(exc["items"]):
            fit("{} {}".format(reason, n), F_SIDE, w - 10, "exclusion item")
            item_line(ax, x + 5.0, x + w - 5.0,
                      top - SIDE_ROW_1 - j * SIDE_ROW_H,
                      reason, n, F_SIDE)

    # --- arrows and stage boxes -------------------------------------------
    for arr in geom["arrows"]:
        arrow_down(ax, arr["x"], arr["y_from"], arr["y_to"])
    for st in geom["stages"]:
        x, top, w, h = st["x"], st["y_top"], st["w"], st["h"]
        last = st["last"]
        rounded(ax, x, top - h, w, h,
                C_ACCENT_SOFT if last else C_NEUTRAL_FILL,
                C_ACCENT if last else C_NEUTRAL_EDGE, lw=1.0 if last else 0.8)
        ax.add_patch(Rectangle((x + 3.0, top - h + 3.0), 2.0, h - 6.0,
                               facecolor=C_ACCENT, edgecolor="none", zorder=3))
        fit(st["title"], F_TITLE, w - 24, "spine title")
        ax.text(x + w / 2.0 + 1.5, top - 9.0, st["title"], fontsize=F_TITLE,
                color=C_INK, ha="center", va="center", zorder=4)
        ax.text(x + w / 2.0 + 1.5, top - 19.0,
                "n = {}".format(st["count"]),
                fontsize=F_COUNT, color=C_ACCENT, ha="center", va="center",
                weight="bold", zorder=4)

    # --- phase rail --------------------------------------------------------
    for band in geom["bands"]:
        top, h = band["y_top"], band["h"]
        ax.add_patch(FancyBboxPatch(
            (band["x"], top - h), BAND_W, h,
            boxstyle="round,pad=0,rounding_size=4",
            linewidth=0.0, facecolor=C_ACCENT_SOFT, zorder=1))
        ax.text(band["x"] + BAND_W / 2.0, top - h / 2.0, band["label"],
                fontsize=F_PHASE, color=C_ACCENT, ha="center", va="center",
                rotation=90, rotation_mode="anchor", weight="bold", zorder=4)

    fig.savefig(OUT_PDF)
    fig.savefig(OUT_SVG)
    fig.savefig(OUT_TIFF, dpi=600, pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(OUT_PNG, dpi=300)
    print("saved {} ({:.1f} x {:.1f} pt, {:.0f} mm wide)".format(
        OUT_PDF.name, W, H, FIG_WIDTH_MM))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
