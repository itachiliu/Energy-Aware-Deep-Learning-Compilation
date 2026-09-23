# -*- coding: utf-8 -*-
"""Redraw figures/energy_ops_chart.pdf (relative energy per operation).

Values follow the normalised 45 nm CMOS figures used in the Eyeriss line of
work: one MAC = 1, register-file access ~= 2, on-chip SRAM access ~= 6,
off-chip DRAM access ~= 200. The DRAM/MAC ratio is the "tens to hundreds"
claim made in the text; Horowitz's per-operation estimates give the same
order (a 32-bit DRAM read is ~200x a 32-bit multiply, and 640 pJ in absolute
terms).

The top axis converts the same normalisation into absolute energy, anchored at
1x = 3.1 pJ (Horowitz's 45 nm 32-bit multiply). Anchoring there keeps the whole
figure on one basis: multiplying the Eyeriss-style ratios by 3.1 pJ reproduces
Horowitz's DRAM figure (200 x 3.1 = 620 pJ ~ 640 pJ). Printing Horowitz's raw
per-operation SRAM number (5 pJ) next to the 6x bar would instead mix two
different normalisations, since 5 pJ is only 1.6x a 32-bit multiply.

The chart is drawn at its final printed size (0.45\textwidth of the two-column
layout) so the type stays at 6.5-7 pt instead of being scaled down, and every
label uses a Roman (Times) face to match the body text.

    python figures/make_energy_ops_chart.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT_PDF = HERE / "energy_ops_chart.pdf"
OUT_PNG = HERE / "energy_ops_chart.png"

# value, label  (top to bottom, as printed)
DATA = [
    (1.0, "MAC (compute)"),
    (2.0, "Register file access"),
    (6.0, "On-chip SRAM access"),
    (200.0, "Off-chip DRAM access"),
]

C_INK = "#1B2733"
C_MUTED = "#8FA9C8"
C_ACCENT = "#1F4E8C"
C_BAR = "#C6D5E6"
C_EDGE = "#7E93AB"


def main():
    assert [v for v, _ in DATA] == [1.0, 2.0, 6.0, 200.0]
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "font.size": 7.0,
        "axes.linewidth": 0.7,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })

    fig = plt.figure(figsize=(3.15, 1.80))
    ax = fig.add_axes([0.335, 0.245, 0.63, 0.575])

    ypos = list(range(len(DATA)))[::-1]          # MAC on top
    values = [v for v, _ in DATA]
    labels = [t for _, t in DATA]
    colors = [C_ACCENT if v > 100 else C_BAR for v in values]

    ax.barh(ypos, values, height=0.56, color=colors, edgecolor=C_EDGE,
            linewidth=0.6, zorder=2)
    for y, v in zip(ypos, values):
        ax.text(v * 1.13, y, "{:g}$\\times$".format(v), va="center",
                ha="left", fontsize=6.5, color=C_INK, zorder=3)

    ax.set_xscale("log")
    ax.set_xlim(0.85, 700)
    ax.set_xticks([1, 10, 100])
    ax.set_xticklabels(["1", "10", "100"], fontsize=6.5)
    ax.set_ylim(-0.6, len(DATA) - 0.4)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.set_xlabel("Relative energy per operation (log scale, MAC = 1)",
                  fontsize=7.0, labelpad=2)
    ax.tick_params(axis="both", length=2.2, width=0.6, pad=1.6)
    ax.grid(False)          # four bars do not need grid lines
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(C_EDGE)

    # absolute-energy scale on top, same normalisation (1x = 3.1 pJ)
    pj_per_unit = 3.1
    secax = ax.secondary_xaxis(
        "top",
        functions=(lambda v: v * pj_per_unit,
                   lambda pj: pj / pj_per_unit))
    secax.set_xticks([pj_per_unit, pj_per_unit * 10, pj_per_unit * 100])
    secax.set_xticklabels(["3.1", "31", "310"])
    secax.set_xlabel("energy per access (pJ, 45 nm)", fontsize=6.5,
                     labelpad=4.0)
    secax.tick_params(labelsize=6.0, length=2.0, width=0.6, pad=1.0)
    secax.spines["top"].set_color(C_EDGE)
    secax.spines["top"].set_linewidth(0.6)

    # standalone note inside the plot area (right of the short MAC bar), so
    # neither the axis nor a tick mark can cross it
    ax.text(4.5, len(DATA) - 1.0, "data movement dominates", fontsize=6.5,
            color=C_ACCENT, ha="left", va="center", zorder=3)

    fig.savefig(OUT_PDF)
    fig.savefig(OUT_PNG, dpi=600)
    print("saved {} ({:.0f} x {:.0f} pt)".format(
        OUT_PDF.name, *fig.get_size_inches() * 72))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
