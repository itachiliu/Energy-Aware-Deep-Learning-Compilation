# -*- coding: utf-8 -*-
"""Redraw Figure 2 (10-class controlled-vocabulary distribution, N=121).

English labels. Horizontal bars sorted by count; values and shares annotated.
Outputs category_distribution_v3.pdf/.png.
"""
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(os.environ.get("TEMP", "/tmp")) / "mplcache"))

import matplotlib
matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
})


HERE = Path(__file__).resolve().parent

DATA = [
    ("Energy & cost modeling", 21),
    ("Loop/operator optimization", 17),
    ("Measurement & benchmarks", 16),
    ("Graph-level optimization", 13),
    ("TinyML & MCU deployment", 12),
    ("AI-for-compiler", 11),
    ("Sparse compilation support", 10),
    ("Heterogeneous scheduling", 8),
    ("DVFS & power-state orchestration", 8),
    ("Time-energy Pareto & carbon", 5),
]


def main():
    total = 121
    labels = [d[0] for d in DATA]
    values = [d[1] for d in DATA]

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    y = range(len(labels))[::-1]
    colors = ["#2b6cb0" if v == max(values) else "#8fb8de" for v in values]
    bars = ax.barh(list(y), values, color=colors, edgecolor="#2b4a6f",
                   linewidth=0.5, height=0.62)

    for yi, v in zip(y, values):
        ax.text(v + 0.25, yi, f"{v}  ({v / total * 100:.0f}%)",
                va="center", fontsize=9, color="#1a1a1a")

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9.5)
    ax.set_xlim(0, 25)
    ax.set_xticks(range(0, 21, 5))
    ax.set_xlabel("Number of studies", fontsize=10)
    ax.set_title("Distribution of the 121 included studies "
                 "across ten controlled-vocabulary categories", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", ls=":", lw=0.5, alpha=0.45)
    ax.set_axisbelow(True)
    fig.tight_layout()

    HERE.mkdir(parents=True, exist_ok=True)
    fig.savefig(HERE / "category_distribution_v3.pdf", dpi=300)
    fig.savefig(HERE / "category_distribution_v3.png", dpi=300)
    print("saved", HERE / "category_distribution_v3.pdf")


if __name__ == "__main__":
    main()
