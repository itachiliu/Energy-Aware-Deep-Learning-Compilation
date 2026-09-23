# -*- coding: utf-8 -*-
"""Publication-year and venue distribution of the 121 coded studies.

Reads audit/appendix-matrix-code.csv and writes
figures/lit_distribution.pdf/.png (two panels), then prints the numbers used in
the manuscript text.

    python job/plot_lit_stats.py
"""
import collections
import csv
import os
import sys
from pathlib import Path

if sys.version_info < (3, 6):
    sys.stderr.write("needs Python 3.6+\n")
    sys.exit(2)

os.environ.setdefault("MPLCONFIGDIR",
                      str(Path(os.environ.get("TEMP", "/tmp")) / "mplcache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "axes.unicode_minus": False,
})

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT.parent / "audit" / "appendix-matrix-code.csv"   # ROOT = experiment/
FIG_DIR = ROOT.parent / "figures"

JOURNALS = {
    "ACM TACO", "IEEE TC", "TMC", "ACM TECS", "ACM TOMPECS", "Digital Commun. Netw.",
    "ETRI J.", "Energies", "FGCS", "IEEE JSSC", "IEEE Micro", "IEEE TCAS-II",
    "IMWUT", "ACM IMWUT", "JETCAS", "Mathematics", "Phil. Trans. A", "TASE",
}

SHORT = {
    "Phil. Trans. A": "Phil. Trans. A",
    "Digital Commun. Netw.": "Digit. Commun. Netw.",
    "GREENS (ICSE workshop)": "GREENS (ICSE ws)",
    "IEEE/ACM CCGrid": "CCGrid",
}


def normalise(v):
    """The coding table spells two venues two ways."""
    if v == "IEEE HPCA":
        return "HPCA"
    if v.startswith("NeurIPS D"):
        return "NeurIPS D&B"
    return v


def main():
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    years = collections.Counter()
    venues = collections.Counter()
    for r in rows:
        venues[normalise(r["Venue"])] += 1
        if r["Year"].strip().isdigit():
            years[int(r["Year"])] += 1

    n_conf = sum(c for v, c in venues.items() if v not in JOURNALS)
    n_jour = sum(c for v, c in venues.items() if v in JOURNALS)
    print("papers: {}  conferences/workshops: {}  journals: {}".format(
        len(rows), n_conf, n_jour))
    print("years: {}".format(sorted(years.items())))
    print("distinct venues: {}".format(len(venues)))
    for v, c in venues.most_common(12):
        print("   {:>3}  {}{}".format(c, v, "  [journal]" if v in JOURNALS else ""))

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.9))

    ax = axes[0]
    ys = sorted(years)
    vals = [years[y] for y in ys]
    ax.bar(ys, vals, color="#4c72b0", width=0.68)
    for y, v in zip(ys, vals):
        ax.text(y, v + 0.35, str(v), ha="center", fontsize=11)
    ax.set_xticks(ys)
    ax.set_xticklabels([str(y) for y in ys], fontsize=9.5, rotation=45,
                       ha="right", rotation_mode="anchor")
    ax.set_ylim(0, max(vals) * 1.22)
    ax.set_xlabel("publication year", fontsize=12.5)
    ax.set_ylabel("studies", fontsize=12.5)
    ax.set_title("(a) 121 coded studies by year", fontsize=13)
    ax.grid(axis="y", ls=":", lw=0.4, alpha=0.5)
    ax.tick_params(labelsize=11)

    ax = axes[1]
    top = venues.most_common(12)
    names = [SHORT.get(v, v) for v, _ in top][::-1]
    counts = [c for _, c in top][::-1]
    colors = ["#dd8452" if v in JOURNALS else "#4c72b0" for v, _ in top][::-1]
    ypos = np.arange(len(names))
    ax.barh(ypos, counts, color=colors, height=0.7)
    for y, c in zip(ypos, counts):
        ax.text(c + 0.15, y, str(c), va="center", fontsize=11)
    ax.set_yticks(ypos)
    ax.set_yticklabels(names, fontsize=11)
    ax.set_xlim(0, max(counts) * 1.18)
    ax.set_xlabel("studies", fontsize=12.5)
    ax.set_title("(b) top venues (orange: journals)", fontsize=13)
    ax.grid(axis="x", ls=":", lw=0.4, alpha=0.5)
    ax.tick_params(labelsize=11)

    fig.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / "lit_distribution.pdf", dpi=300)
    fig.savefig(FIG_DIR / "lit_distribution.png", dpi=300)
    plt.close(fig)
    print("saved", FIG_DIR / "lit_distribution.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
