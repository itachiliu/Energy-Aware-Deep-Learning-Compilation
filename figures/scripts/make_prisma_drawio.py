# -*- coding: utf-8 -*-
"""Emit figures/PRISMA.drawio (editable draw.io / diagrams.net source).

The geometry comes from prisma_layout.py, the same module the matplotlib
renderer uses, so the editable diagram and the submission PDF cannot drift
apart. Page units are points, which draw.io maps 1:1 when exporting at 100 %
(so the exported PDF is 89 mm wide, matching the journal column).

Open with the desktop app or at https://app.diagrams.net (File > Open From >
Device). Export via File > Export as > PDF/SVG at zoom 100 %.

Run:  python figures/make_prisma_drawio.py
"""
from pathlib import Path
from xml.etree import ElementTree as ET

from prisma_layout import (
    C_ACCENT, C_ACCENT_SOFT, C_INK, C_MUTED, C_NEUTRAL_EDGE, C_NEUTRAL_FILL,
    C_RULE, C_SIDE_EDGE, C_SIDE_FILL, C_SIDE_INK, FONT, F_COUNT, F_PHASE,
    F_SIDE, F_SIDE_HDR, F_SRC, F_SRC_SUB, F_TITLE, HERE, SIDE_ROW_1,
    SIDE_ROW_H, layout,
)

OUT = HERE / "PRISMA.drawio"

BASE = "html=1;whiteSpace=wrap;fontFamily={};".format(FONT)


def style(*parts, **kw):
    bits = [BASE] + [p for p in parts if p]
    for key, value in kw.items():
        bits.append("{}={}".format(key, value))
    return ";".join(b.strip(";") for b in bits if b) + ";"


def vertex(cells, cid, value, x, y_top, w, h, cell_style, parent="1"):
    cell = ET.SubElement(cells, "mxCell", {
        "id": cid, "value": value, "style": cell_style, "vertex": "1",
        "parent": parent})
    ET.SubElement(cell, "mxGeometry", {
        "x": "{:.2f}".format(x), "y": "{:.2f}".format(y_top),
        "width": "{:.2f}".format(w), "height": "{:.2f}".format(h),
        "as": "geometry"})
    return cell


def edge(cells, cid, src, dst, cell_style):
    cell = ET.SubElement(cells, "mxCell", {
        "id": cid, "style": cell_style, "edge": "1", "parent": "1",
        "source": src, "target": dst})
    ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    return cell


def depth_first(document, diagram_id="prisma1"):
    root = ET.Element("mxfile", {
        "host": "app.diagrams.net", "agent": "make_prisma_drawio.py",
        "type": "device", "version": "24.7.17"})
    diagram = ET.SubElement(root, "diagram", {
        "id": diagram_id, "name": "PRISMA flow"})
    model = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "600", "dy": "400", "grid": "0", "gridSize": "10",
        "guides": "1", "tooltips": "1", "connect": "1", "arrows": "1",
        "fold": "1", "page": "1", "pageScale": "1",
        "pageWidth": "{:.2f}".format(document["W"]),
        "pageHeight": "{:.2f}".format(document["H"]),
        "math": "0", "shadow": "0"})
    graph_root = ET.SubElement(model, "root")
    ET.SubElement(graph_root, "mxCell", {"id": "0"})
    ET.SubElement(graph_root, "mxCell", {"id": "1", "parent": "0"})
    return root, graph_root


def band_style():
    return style("rounded=1", "arcSize=30", "fillColor=" + C_ACCENT_SOFT,
                 strokeColor="none", fontSize=F_PHASE, fontColor=C_ACCENT,
                 fontStyle="1", horizontal="0", verticalAlign="middle",
                 align="center")


def source_style():
    return style("rounded=1", "arcSize=10", "fillColor=" + C_NEUTRAL_FILL,
                 "strokeColor=" + C_NEUTRAL_EDGE, "strokeWidth=1",
                 fontSize=F_SRC_SUB, fontColor=C_MUTED, verticalAlign="middle",
                 align="center", spacing=2)


def stage_style(last):
    return style("rounded=1", "arcSize=10",
                 "fillColor=" + (C_ACCENT_SOFT if last else C_NEUTRAL_FILL),
                 "strokeColor=" + (C_ACCENT if last else C_NEUTRAL_EDGE),
                 "strokeWidth={}".format(1 if last else 0.8),
                 fontSize=F_TITLE, fontColor=C_INK, verticalAlign="middle",
                 align="center")


def excl_style():
    return style("rounded=1", "arcSize=10", "fillColor=" + C_SIDE_FILL,
                 "strokeColor=" + C_SIDE_EDGE,
                 "strokeWidth=1", fontSize=F_SIDE_HDR, fontColor=C_SIDE_INK,
                 verticalAlign="top", align="left", spacingLeft=5,
                 spacingTop=3.5, spacingRight=5)


def item_style(align):
    return style("rounded=0", "fillColor=none", "strokeColor=none",
                 fontSize=F_SIDE,
                 fontColor=C_INK if align == "left" else C_SIDE_INK,
                 fontStyle="0" if align == "left" else "1",
                 verticalAlign="middle", align=align, spacingLeft=0,
                 spacingRight=0)


def main():
    geom = layout()
    W, H = geom["W"], geom["H"]
    root, cells = depth_first(geom)

    for i, band in enumerate(geom["bands"], 1):
        top = band["y_top"]
        vertex(cells, "band{}".format(i), band["label"], band["x"],
               H - top, 13.0, band["h"], band_style())

    source_ids = []
    for i, src in enumerate(geom["sources"], 1):
        lines = "<br>".join(
            '<span style="font-size:{:.1f}px;color:{}">{}</span>'.format(
                F_SRC_SUB, C_MUTED, ln) for ln in src["lines"])
        value = ('<span style="font-size:{:.1f}px;color:{};font-weight:bold">'
                 "{}&nbsp;&nbsp;n = {}</span><br>{}").format(
                     F_SRC, C_ACCENT, src["title"], src["total"], lines)
        cid = "source{}".format(i)
        source_ids.append(cid)
        vertex(cells, cid, value, src["x"], H - src["y_top"], src["w"],
               src["h"], source_style())

    stage_ids = []
    for i, st in enumerate(geom["stages"], 1):
        value = ("<b>{}</b><br>"
                 '<span style="font-size:{:.1f}px;color:{};font-weight:bold">'
                 "n = {}</span>").format(st["title"], F_COUNT, C_ACCENT,
                                         st["count"])
        cid = "stage{}".format(i)
        stage_ids.append(cid)
        vertex(cells, cid, value, st["x"], H - st["y_top"], st["w"],
               st["h"], stage_style(st["last"]))
        # accent stripe on the left edge of every stage box (moves with it)
        vertex(cells, "{}_stripe".format(cid), "", 3.0, 3.0, 2.0,
               st["h"] - 6.0,
               style("rounded=0", "fillColor=" + C_ACCENT,
                     "strokeColor=none"), parent=cid)

    for i, exc in enumerate(geom["exclusions"], 1):
        top = exc["y_top"]
        header = ('<span style="font-size:{:.1f}px;color:{};font-weight:bold">'
                  "{}</span><br>"
                  '<span style="font-size:{:.1f}px;color:{}">{}</span>').format(
                      F_SIDE_HDR, C_SIDE_INK, exc["header"], F_SIDE, C_MUTED,
                      exc["subtotal"])
        cid = "excl{}".format(i)
        vertex(cells, cid, header, exc["x"], H - top, exc["w"], exc["h"],
               excl_style())
        # item rows: reason on the left, count right-aligned in its own cell;
        # both are children so the block stays a single movable object
        for j, (reason, n) in enumerate(exc["items"], 1):
            row_top = SIDE_ROW_1 + (j - 1) * SIDE_ROW_H - 4.0
            vertex(cells, "{}_r{}".format(cid, j), reason, 5.0, row_top,
                   exc["w"] - 22.0, 8.0, item_style("left"), parent=cid)
            vertex(cells, "{}_c{}".format(cid, j), str(n),
                   exc["w"] - 17.0, row_top, 12.0, 8.0, item_style("right"),
                   parent=cid)

    flow = style("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;",
                 "strokeColor=" + C_NEUTRAL_EDGE, "strokeWidth=1",
                 "endArrow=block", "endFill=1", "exitX=0.5", "exitY=1",
                 "entryX=0.5", "entryY=0")
    flow_wide = style("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;",
                      "strokeColor=" + C_NEUTRAL_EDGE, "strokeWidth=1",
                      "endArrow=block", "endFill=1", "exitX=0.5", "exitY=1",
                      "entryY=0")
    link = style("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;",
                 "strokeColor=" + C_RULE, "strokeWidth=0.8", "endArrow=none",
                 "exitX=1", "exitY=0.5", "entryX=0", "entryY=0.5")
    # the two identification boxes converge on the first stage box without
    # stacking their arrowheads on one point
    for i, sid in enumerate(source_ids):
        edge(cells, "e_src{}".format(i + 1), sid, stage_ids[0],
             flow_wide + "entryX={:.2f};".format(0.35 + 0.3 * i))
    for i in range(len(stage_ids) - 1):
        edge(cells, "e_stage{}".format(i + 1), stage_ids[i], stage_ids[i + 1],
             flow)
    for i, cid in enumerate(("excl1", "excl2", "excl3")):
        edge(cells, "e_excl{}".format(i + 1), stage_ids[i], cid, link)

    ET.indent(root, space="  ")
    OUT.write_bytes(ET.tostring(root, encoding="utf-8",
                                xml_declaration=True))
    print("saved {} ({:.1f} x {:.1f} page units, {} cells)".format(
        OUT.name, W, H, len(list(cells))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
