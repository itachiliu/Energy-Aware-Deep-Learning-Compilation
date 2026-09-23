# -*- coding: utf-8 -*-
"""Proposal for a matrix-shaped framework figure (NOT used in the paper yet).

The text calls the organising framework a two-dimensional matrix; this render
shows what such a figure could look like: optimisation granularity (rows) x
decision mechanism (columns), each cell carrying the number of included
studies and up to three representative works, with the empty combinations
marked.

    python figures/make_matrix_view_proposal.py
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT_PDF = HERE / "proposed_matrix_view.pdf"
OUT_PNG = HERE / "proposed_matrix_view.png"

# (data key, display label)
GRAN = [("Graph", "Graph"), ("Loop/Op", "Loop / Op"),
        ("Placement", "Placement"), ("Power", "Power state")]
MECH = ["Analytical", "Learned", "AutoSearch", "Agentic"]
# cells with no representative work at all (bold zero in the paper's table)
EMPTY = {("Placement", "Agentic"), ("Power", "Agentic")}
# cells whose coded count is zero but which have a non-statistical
# representative discussed in the text (dagger in the paper's table)
DAGGER = {("Graph", "Agentic")}

C_INK = "#1B2733"
C_MUTED = "#5A6B7B"
C_ACCENT = "#1F4E8C"
C_EDGE = "#B7C7D8"
RAMP = ["#F4F8FC", "#DCE8F5", "#BBD3EC", "#8FB6DE", "#5E93C9"]


def load():
    coding = list(csv.DictReader(
        (ROOT / "supplements" / "coding-121-final.csv").open(encoding="utf-8-sig")))
    names = {}
    for row in csv.DictReader(
            (ROOT / "supplements" / "appendix-matrix-code.csv").open(encoding="utf-8-sig")):
        full = row["Name"]
        short = full.split("：")[-1] if "：" in full else full
        for sep in (" / ", " （", " (", "：", ":"):
            short = short.split(sep)[0]
        short = short.strip()
        names[row["S"]] = short if len(short) <= 14 else short[:13].rstrip() + "\u2026"
    cells = {}
    for r in coding:
        key = (r["granularity"], r["mechanism"])
        cells.setdefault(key, []).append((r["sample_id"], names.get(r["sample_id"], "")))
    return cells


def main():
    cells = load()
    total = sum(len(v) for k, v in cells.items()
                if k[0] in [g for g, _ in GRAN] and k[1] in MECH)
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "figure.facecolor": "white",
    })
    fig = plt.figure(figsize=(3.45, 3.05))
    ax = fig.add_axes([0.185, 0.105, 0.79, 0.775])
    ax.set_xlim(0, len(MECH))
    ax.set_ylim(0, len(GRAN))
    ax.invert_yaxis()
    ax.axis("off")

    counts = {k: len(v) for k, v in cells.items()}
    vmax = max(counts.get((g, m), 0) for g, _ in GRAN for m in MECH)

    for j, mech in enumerate(MECH):
        ax.text(j + 0.5, -0.14, mech, ha="center", va="bottom",
                fontsize=6.4, color=C_INK, fontweight="bold")
    for i, (gkey, glabel) in enumerate(GRAN):
        ax.text(-0.08, i + 0.5, glabel, ha="right", va="center", fontsize=6.4,
                color=C_INK, fontweight="bold")
        for j, mech in enumerate(MECH):
            n = counts.get((gkey, mech), 0)
            shade = RAMP[min(len(RAMP) - 1,
                             int(round(n / float(vmax) * (len(RAMP) - 1))))]
            empty = (gkey, mech) in EMPTY
            ax.add_patch(Rectangle((j + 0.03, i + 0.03), 0.94, 0.94,
                                   facecolor="#F7F7F7" if empty else shade,
                                   edgecolor=C_EDGE, linewidth=0.6, zorder=1))
            if empty:
                ax.text(j + 0.5, i + 0.5, "no work", ha="center",
                        va="center", fontsize=5.0, color=C_MUTED, zorder=3)
                continue
            if (gkey, mech) in DAGGER:
                ax.text(j + 0.46, i + 0.5, "0$^{\\dagger}$", ha="center",
                        va="center", fontsize=7.6, color=C_MUTED, zorder=3)
                continue
            ax.text(j + 0.5, i + 0.28, str(n), ha="center", va="center",
                    fontsize=8.5, color=C_ACCENT if n == vmax else C_INK,
                    fontweight="bold", zorder=3)
            picks = [nm for _, nm in sorted(cells[(gkey, mech)])[:3]]
            for k, nm in enumerate(picks):
                ax.text(j + 0.5, i + 0.50 + k * 0.19, nm, ha="center",
                        va="center", fontsize=5.2, color=C_MUTED, zorder=3)

    fig.text(0.5, 0.975, "Optimisation granularity $\\times$ decision mechanism",
             ha="center", va="center", fontsize=7.0, color=C_INK)
    fig.text(0.5, 0.048,
             "cell = included studies ($n={}$), with up to three "
             "representative works".format(total),
             ha="center", va="center", fontsize=5.4, color=C_MUTED)
    fig.text(0.5, 0.012,
             "$^{\\dagger}$ coded count 0; a representative is discussed in "
             "the text and is not counted as a gap",
             ha="center", va="center", fontsize=5.0, color=C_MUTED)
    fig.savefig(OUT_PDF)
    fig.savefig(OUT_PNG, dpi=600)
    print("saved", OUT_PDF.name, "(n = {})".format(total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
