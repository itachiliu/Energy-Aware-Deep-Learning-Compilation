# -*- coding: utf-8 -*-
"""Advanced figure for the 36-config scan (2 rows x 3 columns), v4.

Row 1: per-model log-log scatter with plain-number ticks; open-ring markers
       mark the latency-optimal point and the energy-optimal point.
Row 2: (b) ORT graph-opt effect (categorical x-axis);
       (c) batch scaling of per-image energy;
       (d) H2 divergence (no in-axes legend; meaning goes in the caption).
"""
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(os.environ.get("TEMP", "/tmp")) / "mplcache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
RAW = BASE / "scan_out_20260908_012226_v2" / "scan_out_20260908_012226" \
    / "results_scan.csv"
OUT_PDF = BASE.parent / "Figures" / "experiment_scan_v2_multi6.pdf"
OUT_PNG = BASE.parent / "Figures" / "experiment_scan_v2_multi6.png"

MODELS = ["mobilenetv2", "resnet50", "vit_b_16"]
MODEL_LABEL = {"mobilenetv2": "MobileNetV2", "resnet50": "ResNet-50",
               "vit_b_16": "ViT-B/16"}
MODEL_COLOR = {"mobilenetv2": "#1f77b4", "resnet50": "#d62728",
               "vit_b_16": "#2ca02c"}
BATCH_COLOR = {1: "#1f77b4", 16: "#ff7f0e"}

STACK_MARK = {
    ("ort-cuda", "0"): "v", ("ort-cuda", "1"): "^",
    ("ort-cuda", "2"): "s", ("ort-cuda", "99"): "o",
    ("torch-eager", "fp32"): "D", ("torch-eager", "fp16"): "P",
}
STACK_LABEL = {
    ("ort-cuda", "0"): "ORT disable", ("ort-cuda", "1"): "ORT basic",
    ("ort-cuda", "2"): "ORT extended", ("ort-cuda", "99"): "ORT all",
    ("torch-eager", "fp32"): "eager FP32", ("torch-eager", "fp16"): "eager FP16",
}


def stack_key(r):
    if r["backend"] == "ort-cuda":
        return (r["backend"], str(int(r["graph_opt_level"])))
    return (r["backend"], r["precision"])


def plain_formatter():
    return mticker.FuncFormatter(lambda v, _: f"{v:g}")


def pick_ticks(vmin, vmax, candidates):
    lo, hi = vmin * 0.9, vmax * 1.1
    return [t for t in candidates if lo <= t <= hi]


def apply_plain_ticks(ax, xvals, yvals):
    """Explicit plain-number tick labels (never scientific)."""
    ax.set_xticks(xvals)
    ax.set_xticklabels([f"{v:g}" for v in xvals])
    ax.set_yticks(yvals)
    ax.set_yticklabels([f"{v:g}" for v in yvals])
    ax.tick_params(which="minor", labelbottom=False, labelleft=False)


def main():
    df = pd.read_csv(RAW)
    df["graph_opt_level"] = df["graph_opt_level"].fillna("")
    agg = df.groupby(
        ["model", "backend", "precision", "batch", "graph_opt_level"],
        as_index=False,
    ).agg(
        lat=("mean_lat_ms", "mean"),
        j=("energy_j_per_inf", "mean"),
        edp=("edp", "mean"),
        power=("mean_power_w", "mean"),
        idle=("idle_power_w", "mean"),
    )
    agg["batch"] = agg["batch"].astype(int)
    agg["j_per_img"] = agg["j"] / agg["batch"]
    agg["static"] = agg["idle"] / agg["power"] * 100.0

    fig = plt.figure(figsize=(12.2, 7.3))
    gs = fig.add_gridspec(2, 3, hspace=0.52, wspace=0.30,
                          left=0.115, right=0.985, top=0.93, bottom=0.19)
    axes = [[fig.add_subplot(gs[r, c]) for c in range(3)] for r in range(2)]

    # -------- row 0: per-model scatter --------
    for col, model in enumerate(MODELS):
        ax = axes[0][col]
        sub = agg[agg["model"] == model]
        # faint ordered path through the four ORT opt levels per batch
        for b in (1, 16):
            ort = sub[(sub["backend"] == "ort-cuda") & (sub["batch"] == b)]
            ort = ort.sort_values("graph_opt_level")
            ax.plot(ort["lat"], ort["j"], ls="-", color="grey", lw=0.9,
                    alpha=0.55, zorder=1)
        for _, r in sub.iterrows():
            mk = STACK_MARK[stack_key(r)]
            b = int(r["batch"])
            ax.loglog(r["lat"], r["j"], marker=mk, color=BATCH_COLOR[b],
                      ms=7.0, ls="none", alpha=0.9, mew=0.7,
                      markerfacecolor="none" if b == 16 else BATCH_COLOR[b])

        ax.grid(which="both", ls=":", lw=0.3, alpha=0.4)
        ax.tick_params(labelsize=7.5)
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        apply_plain_ticks(ax,
                          pick_ticks(xmin, xmax, [1.5, 2, 3, 5, 10, 20, 40]),
                          pick_ticks(ymin, ymax, [0.2, 0.3, 0.5, 1, 2, 3, 5, 10]))

        # open rings mark latency-opt (circle) and energy-opt (square)
        bl = sub.loc[sub["lat"].idxmin()]
        be = sub.loc[sub["j"].idxmin()]
        ax.scatter(bl["lat"], bl["j"], marker="o", s=150, facecolor="none",
                   edgecolor="black", lw=1.5, zorder=5)
        if stack_key(bl) != stack_key(be):
            ax.scatter(be["lat"], be["j"], marker="s", s=150, facecolor="none",
                       edgecolor="black", lw=1.5, zorder=5)

        ax.set_title(MODEL_LABEL[model], fontsize=10)
        ax.set_xlabel("latency (ms / batch call)", fontsize=8.5, labelpad=2)
        if col == 0:
            ax.set_ylabel("J / batch call, gross", fontsize=8.5, labelpad=6)

    # -------- (b) ORT graph-opt effect (categorical x) --------
    ax = axes[1][0]
    levels = [0, 1, 2, 99]
    xcat = np.arange(len(levels))
    for model in MODELS:
        for b in (1, 16):
            s = agg[(agg["model"] == model) & (agg["batch"] == b) &
                    (agg["backend"] == "ort-cuda")]
            s = s.copy()
            s["gl"] = s["graph_opt_level"].astype(float)
            base = s.loc[s["gl"] == float(levels[0]), "j"].iloc[0]
            rel = [s.loc[s["gl"] == float(lev), "j"].iloc[0] / base
                   for lev in levels]
            ax.plot(xcat, rel, marker="o", ms=5.0, lw=1.5,
                    color=MODEL_COLOR[model],
                    ls="-" if b == 1 else "--")
    ax.axhline(1.0, color="grey", lw=0.7, ls=":")
    ax.set_xticks(xcat)
    ax.set_xticklabels(["disable", "basic", "extended", "all"],
                       fontsize=6.2, rotation=24, ha="right")
    ax.set_xlabel("ORT graph optimization level", fontsize=8.5, labelpad=2)
    ax.set_ylabel("relative J/inf (disable = 1)", fontsize=8.5, labelpad=3)
    ax.set_title("(b) graph-opt level is not a free lunch", fontsize=9.5)
    ax.grid(which="both", ls=":", lw=0.3, alpha=0.4)
    ax.tick_params(labelsize=7)
    ax.text(0.02, 0.98, "solid: batch 1\ndash: batch 16", transform=ax.transAxes,
            fontsize=6.2, va="top", color="#333333")

    # -------- (c) batch scaling --------
    ax = axes[1][1]
    xpos = np.arange(6)
    labels = ["MN2\nORT", "MN2\neFP16", "RN50\nORT", "RN50\neFP16",
              "ViT\nORT", "ViT\neFP16"]
    w = 0.34
    for k, (model, kind) in enumerate(
            [("mobilenetv2", "ort"), ("mobilenetv2", "eager"),
             ("resnet50", "ort"), ("resnet50", "eager"),
             ("vit_b_16", "ort"), ("vit_b_16", "eager")]):
        if kind == "ort":
            s = agg[(agg["model"] == model) & (agg["backend"] == "ort-cuda") &
                    (agg["graph_opt_level"] == 2)]
        else:
            s = agg[(agg["model"] == model) & (agg["backend"] == "torch-eager") &
                    (agg["precision"] == "fp16")]
        by_batch = {int(r["batch"]): r["j_per_img"] for _, r in s.iterrows()}
        v1 = by_batch.get(1)
        v16 = by_batch.get(16)
        ax.bar(xpos[k] - w / 2, v1, w, color=BATCH_COLOR[1], log=True)
        ax.bar(xpos[k] + w / 2, v16, w, color=BATCH_COLOR[16], log=True)
    ax.set_xticks(xpos)
    ax.set_xticklabels(labels, fontsize=6)
    ax.set_ylabel("J per image, gross", fontsize=8.5, labelpad=3)
    ax.set_title("(c) batching amortizes per-image energy", fontsize=9.5)
    ax.grid(axis="y", which="both", ls=":", lw=0.3, alpha=0.4)
    ax.tick_params(labelsize=7)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BATCH_COLOR[b])
                       for b in (1, 16)],
              labels=["batch 1", "batch 16"], fontsize=7, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, 1.04), ncol=2)

    # -------- (d) H2 trade-off --------
    ax = axes[1][2]
    label_offset = {
        ("mobilenetv2", 16): (4, -4),
        ("resnet50", 1): (-2, -4),
        ("resnet50", 16): (6, 2),
        ("vit_b_16", 1): (4, 4),
    }
    for model in MODELS:
        for b in (1, 16):
            s = agg[(agg["model"] == model) & (agg["batch"] == b)]
            bl = s.loc[s["lat"].idxmin()]
            be = s.loc[s["j"].idxmin()]
            if stack_key(bl) == stack_key(be):
                ax.scatter(0, 0, color=MODEL_COLOR[model], s=14,
                           edgecolors="grey", linewidths=0.3, zorder=3)
                continue
            lat_pen = (bl["lat"] / be["lat"] - 1.0) * 100
            eng_sav = (1.0 - be["j"] / bl["j"]) * 100
            edp_wins_energy = be["edp"] < bl["edp"]
            ax.scatter(lat_pen, eng_sav, color=MODEL_COLOR[model],
                       marker="*" if edp_wins_energy else "o", s=45,
                       edgecolors="k", linewidths=0.3, zorder=3)
            dx, dy = label_offset.get((model, b), (3, 3))
            ax.annotate(f"{MODEL_LABEL[model]} b{b}",
                        xy=(lat_pen, eng_sav),
                        xytext=(lat_pen + dx, eng_sav + dy),
                        fontsize=6.5, ha="left", va="bottom")
    ax.axhline(0, color="grey", lw=0.6)
    ax.axvline(0, color="grey", lw=0.6)
    ax.set_xlabel("latency penalty of E-opt config (%)", fontsize=8.5, labelpad=2)
    ax.set_ylabel("energy saving of E-opt config (%)", fontsize=8.5, labelpad=3)
    ax.set_title("(d) H2 divergence: penalty vs. saving", fontsize=9.5)
    ax.grid(which="both", ls=":", lw=0.3, alpha=0.4)
    ax.tick_params(labelsize=7)
    ax.margins(0.16, 0.16)

    # -------- shared legend at the bottom --------
    handles = []
    for key, lab in STACK_LABEL.items():
        handles.append(plt.Line2D([], [], marker=STACK_MARK[key], ls="none",
                                  color="black", ms=6.5, label=lab))
    for b in (1, 16):
        handles.append(plt.Line2D([], [], marker="o", ls="none",
                                  markerfacecolor=BATCH_COLOR[b], color=BATCH_COLOR[b],
                                  ms=6.5, label=f"batch {b}"))
    handles += [plt.Line2D([], [], marker="o", ls="none", mfc="none",
                           mec="black", ms=7.0, label="ring: latency-opt"),
                plt.Line2D([], [], marker="s", ls="none", mfc="none",
                           mec="black", ms=7.0, label="ring: energy-opt")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.02),
               ncol=10, fontsize=6.6, frameon=False, columnspacing=1.3,
               handletextpad=0.25)

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PDF, dpi=300)
    fig.savefig(OUT_PNG, dpi=300)
    print("saved", OUT_PDF, OUT_PNG)


if __name__ == "__main__":
    main()
