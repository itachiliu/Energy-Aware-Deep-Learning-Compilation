# -*- coding: utf-8 -*-
"""Render a draw.io file to a single-page PDF with matplotlib.

The editable diagram (figures/PRISMA.drawio) is the source of truth for Figure
2; this script turns it into the vector PDF the manuscript includes, so edits
made in draw.io survive without hand-copying them into the plotting code.

Supported subset of draw.io: rounded rectangles, solid fills and strokes,
left/centre/right and top/middle/bottom aligned labels, inline <b>/<font>/<span>
runs with per-run size, colour and weight, <br> line breaks, entities,
horizontal=0 rotated labels, and orthogonal edges with block arrowheads.

    python Figures/render_drawio.py figures/PRISMA.drawio figures/PRISMA.drawio.pdf
"""
import re
import sys
from html import unescape
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Polygon
from matplotlib.textpath import TextPath

DEFAULT_FONT = "Microsoft YaHei"
FONT_SIZE_KEYS = ("fontSize", "font-size")
TAG_RE = re.compile(r"<br\s*/?>|</?[a-zA-Z][^>]*>")
STYLE_RE = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;]+)")


# ------------------------------------------------------------------ parse ---
def parse_style(text):
    out = {}
    for part in (text or "").split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def parse_color(value, default):
    if not value or value in ("none", "default"):
        return default
    value = value.strip()
    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", value)
    if m:
        return "#{:02X}{:02X}{:02X}".format(*(int(g) for g in m.groups()))
    if value.startswith("#"):
        return value.upper()
    return default


def parse_inline(tag_style, run):
    """Apply an inline style attribute on top of the running style."""
    for key, value in STYLE_RE.findall(tag_style or ""):
        key, value = key.strip().lower(), value.strip()
        if key in FONT_SIZE_KEYS:
            m = re.match(r"([\d.]+)", value)
            if m:
                run["size"] = float(m.group(1))
        elif key == "color":
            run["color"] = parse_color(value, run["color"])
        elif key == "font-weight":
            run["bold"] = value in ("bold", "700", "800", "900")


def parse_value(html, base):
    """draw.io label HTML -> list of lines, each a list of styled runs."""
    lines, current, stack = [], [], []
    run = dict(base)
    pos = 0
    for match in TAG_RE.finditer(html or ""):
        text = html[pos:match.start()]
        if text:
            current.append(dict(run, text=unescape(text).replace("\u00a0", " ")))
        tag = match.group(0)
        pos = match.end()
        if tag.lower().startswith("<br"):
            lines.append(current)
            current = []
            continue
        if tag.startswith("</"):
            if stack:
                run = stack.pop()
            continue
        stack.append(dict(run))
        name = re.match(r"<([a-zA-Z]+)", tag).group(1).lower()
        if name in ("b", "strong"):
            run["bold"] = True
        elif name in ("i", "em"):
            run["italic"] = True
        style = re.search(r'style\s*=\s*"([^"]*)"', tag)
        if style:
            parse_inline(style.group(1), run)
    text = (html or "")[pos:]
    if text:
        current.append(dict(run, text=unescape(text).replace("\u00a0", " ")))
    lines.append(current)
    cleaned = []
    for line in lines:
        runs = [r for r in line if r["text"].strip()]
        cleaned.append(runs)
    return cleaned or [[]]


# --------------------------------------------------------------- geometry ---
def cell_rect(cell, cells):
    geo = cell.find("mxGeometry")
    x = float(geo.get("x", 0.0))
    y = float(geo.get("y", 0.0))
    w = float(geo.get("width", 0.0))
    h = float(geo.get("height", 0.0))
    parent = cells.get(cell.get("parent"))
    if parent is not None and parent.get("vertex") == "1":
        px, py, _, _ = cell_rect(parent, cells)
        x += px
        y += py
    return x, y, w, h


def text_width(text, size, bold, font):
    if not text:
        return 0.0
    prop = FontProperties(family=font, weight="bold" if bold else "normal")
    return TextPath((0, 0), text, size=size, prop=prop).get_extents().width


def draw_label(ax, cell, style, rect, font, report):
    x, y, w, h = rect
    base_size = float(style.get("fontSize", 10.0))
    base = {"size": base_size,
            "color": parse_color(style.get("fontColor"), "#1B2733"),
            "bold": style.get("fontStyle") == "1", "italic": False}
    lines = parse_value(cell.get("value") or "", base)
    lines = [ln for ln in lines if ln]
    if not lines:
        return

    if style.get("horizontal") == "0":
        text = " ".join(r["text"] for line in lines for r in line).strip()
        size = max(r["size"] for line in lines for r in line)
        colour = lines[0][0]["color"]
        bold = any(r["bold"] for line in lines for r in line)
        if text_width(text, size, bold, font) > h - 2 or size > w - 2:
            report.append(("rotated label may not fit", text[:24], rect))
        ax.text(x + w / 2.0, y + h / 2.0, text, fontsize=size, color=colour,
                weight="bold" if bold else "normal", ha="center", va="center",
                rotation=90, rotation_mode="anchor", zorder=4,
                fontfamily=font)
        return

    # draw.io wraps labels that are wider than their box
    avail = w - float(style.get("spacingLeft", 0.0)) - float(
        style.get("spacingRight", 0.0))
    if style.get("whiteSpace", "wrap") != "nowrap":
        wrapped = []
        for line in lines:
            text = "".join(r["text"] for r in line)
            if text_width(text, max((r["size"] for r in line), default=10.0),
                          any(r["bold"] for r in line), font) <= avail:
                wrapped.append(line)
                continue
            size = max(r["size"] for r in line)
            bold = any(r["bold"] for r in line)
            colour = line[0]["color"]
            words, current = text.split(" "), ""
            for word in words:
                candidate = (current + " " + word).strip()
                if current and text_width(candidate, size, bold, font) > avail:
                    wrapped.append([dict(line[0], text=current)])
                    current = word
                else:
                    current = candidate
            if current:
                wrapped.append([dict(line[0], text=current, color=colour)])
        lines = wrapped

    heights = [max(r["size"] for r in line) * 1.28 for line in lines]
    block = sum(heights)
    align = style.get("align", "center")
    valign = style.get("verticalAlign", "middle")
    pad_l = float(style.get("spacingLeft", 0.0))
    pad_r = float(style.get("spacingRight", 0.0))
    pad_t = float(style.get("spacingTop", 0.0))
    pad_b = float(style.get("spacingBottom", 0.0))
    if valign == "top":
        top = y + pad_t
    elif valign == "bottom":
        top = y + h - block - pad_b + pad_t
    else:
        top = y + (h - block) / 2.0 + pad_t

    cursor = top
    for line, line_h in zip(lines, heights):
        width = sum(text_width(r["text"], r["size"], r["bold"], font)
                    for r in line)
        if align == "left":
            start = x + pad_l
        elif align == "right":
            start = x + w - pad_r - width
        else:
            start = x + w / 2.0 - width / 2.0
        if start < x + pad_l - 0.6 or start + width > x + w - pad_r + 0.6:
            report.append(("label wider than its box", line[0]["text"][:24],
                           (x, y, w, h)))
        cx = start
        for run in line:
            rw = text_width(run["text"], run["size"], run["bold"], font)
            ax.text(cx, cursor + line_h / 2.0, run["text"],
                    fontsize=run["size"], color=run["color"],
                    weight="bold" if run["bold"] else "normal", ha="left",
                    va="center", zorder=4, fontfamily=font)
            cx += rw
        cursor += line_h


def draw_edge(ax, cell, style, rects):
    src = rects.get(cell.get("source"))
    dst = rects.get(cell.get("target"))
    if not src or not dst:
        return
    colour = parse_color(style.get("strokeColor"), "#B7C7D8")
    lw = float(style.get("strokeWidth", 1.0))
    ex = float(style.get("exitX", 0.5))
    ey = float(style.get("exitY", 0.5))
    nx = float(style.get("entryX", 0.5))
    ny = float(style.get("entryY", 0.5))
    p0 = (src[0] + ex * src[2], src[1] + ey * src[3])
    p1 = (dst[0] + nx * dst[2], dst[1] + ny * dst[3])
    head = 5.0 if style.get("endArrow", "block") == "block" else 0.0
    points = []
    if abs(p0[0] - p1[0]) < 0.5:                      # straight vertical
        points = [p0, (p1[0], p1[1] + head)]
    elif abs(p0[1] - p1[1]) < 0.5:                    # straight horizontal
        points = [p0, (p1[0] - head, p1[1])]
    elif ey >= 1.0:                                    # down, across, down
        mid = (p0[1] + p1[1]) / 2.0
        points = [p0, (p0[0], mid), (p1[0], mid), (p1[0], p1[1] + head)]
    elif ex >= 1.0:                                    # right, down/up, right
        mid = (p0[0] + p1[0]) / 2.0
        points = [p0, (mid, p0[1]), (mid, p1[1]), (p1[0] - head, p1[1])]
    else:
        points = [p0, p1]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.plot(xs, ys, color=colour, lw=lw, zorder=1, solid_capstyle="butt")
    if head:
        last, prev = points[-1], points[-2]
        if abs(last[0] - prev[0]) > abs(last[1] - prev[1]):
            tip = (p1[0], p1[1])
            tri = [tip, (tip[0] - head, tip[1] - head * 0.45),
                   (tip[0] - head, tip[1] + head * 0.45)]
        else:
            tip = (p1[0], p1[1])
            tri = [tip, (tip[0] - head * 0.45, tip[1] + head),
                   (tip[0] + head * 0.45, tip[1] + head)]
        ax.add_patch(Polygon(tri, closed=True, facecolor=colour,
                             edgecolor="none", zorder=1))


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "figures/PRISMA.drawio")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else src.with_suffix(".pdf"))
    root = ET.parse(src).getroot()
    model = root.find("diagram").find("mxGraphModel")
    W = float(model.get("pageWidth"))
    H = float(model.get("pageHeight"))
    cells = {c.get("id"): c for c in model.iter("mxCell")}
    font = DEFAULT_FONT

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [font, "DejaVu Sans"],
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })
    fig = plt.figure(figsize=(W / 72.0, H / 72.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)          # draw.io coordinates are top-down
    ax.axis("off")

    report, rects = [], {}
    for cell in model.iter("mxCell"):
        if cell.get("vertex") == "1":
            rects[cell.get("id")] = cell_rect(cell, cells)

    for cell in model.iter("mxCell"):
        if cell.get("vertex") != "1":
            continue
        rect = rects[cell.get("id")]
        style = parse_style(cell.get("style"))
        fill = parse_color(style.get("fillColor"), None)
        stroke = parse_color(style.get("strokeColor"), None)
        lw = float(style.get("strokeWidth", 1.0))
        if fill or stroke:
            radius = 0.0
            if style.get("rounded") == "1":
                radius = min(rect[2], rect[3]) * float(
                    style.get("arcSize", 15)) / 100.0
            ax.add_patch(FancyBboxPatch(
                (rect[0], rect[1]), rect[2], rect[3],
                boxstyle="round,pad=0,rounding_size={:.2f}".format(radius),
                linewidth=lw if stroke else 0.0,
                edgecolor=stroke or "none", facecolor=fill or "none",
                zorder=2, mutation_aspect=1.0))
        draw_label(ax, cell, style, rect, font, report)

    for cell in model.iter("mxCell"):
        if cell.get("edge") == "1":
            draw_edge(ax, cell, parse_style(cell.get("style")), rects)

    fig.savefig(out)
    print("rendered {} -> {} ({:.1f} x {:.1f} pt)".format(
        src.name, out.name, W, H))
    if report:
        print("{} layout warnings:".format(len(report)))
        for what, text, rect in report:
            print("   {}: '{}' in box ({:.1f}, {:.1f}, {:.1f}, {:.1f})".format(
                what, text, *rect))
    else:
        print("no layout warnings: every label fits its box")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
