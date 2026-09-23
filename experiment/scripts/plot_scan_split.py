# -*- coding: utf-8 -*-
"""Generate the 36-config scan panels as separate figure files.

Files written under <repo>/Figures/:
  exp_scan_scatter_<model>.pdf/.png   one log-log scatter per model
  exp_scan_ort_opt.pdf/.png           ORT graph-opt effect
  exp_scan_batch.pdf/.png             batch scaling of per-image energy
  exp_scan_h2.pdf/.png                H2 latency-penalty vs energy-saving
"""
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(os.environ.get("TEMP", "/tmp")) / "mplcache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "axes.unicode_minus": False,
})


BASE = Path(__file__).resolve().parent
RAW = BASE / "scan_out_20260908_012226_v2" / "results_scan.csv"
FIG_DIR = BASE.parent / "Figures"

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


def load_agg():
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
    return agg


def save(fig, stem):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{stem}.pdf", dpi=300)
    fig.savefig(FIG_DIR / f"{stem}.png", dpi=300)
    plt.close(fig)
    print("saved", FIG_DIR / f"{stem}.pdf")


def style_ax(ax):
    ax.grid(which="both", ls=":", lw=0.3, alpha=0.4)
    ax.tick_params(labelsize=9)


def plain_ticks(ax):
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    lo_x, hi_x = xmin * 0.9, xmax * 1.1
    lo_y, hi_y = ymin * 0.9, ymax * 1.1
    xt = [v for v in (1.5, 2, 3, 5, 10, 20, 40) if lo_x <= v <= hi_x]
    yt = [v for v in (0.2, 0.3, 0.5, 1, 2, 3, 5, 10) if lo_y <= v <= hi_y]
    ax.set_xticks(xt)
    ax.set_xticklabels([f"{v:g}" for v in xt])
    ax.set_yticks(yt)
    ax.set_yticklabels([f"{v:g}" for v in yt])
    ax.tick_params(which="minor", labelbottom=False, labelleft=False)


def scatter_figure(model, agg):
    fig, ax = plt.subplots(figsize=(4.4, 3.6))
    sub = agg[agg["model"] == model]
    for b in (1, 16):
        ort = sub[(sub["backend"] == "ort-cuda") & (sub["batch"] == b)]
        ort = ort.sort_values("graph_opt_level")
        ax.plot(ort["lat"], ort["j"], ls="-", color="grey", lw=1.0,
                alpha=0.55, zorder=1)
    for _, r in sub.iterrows():
        mk = STACK_MARK[stack_key(r)]
        b = int(r["batch"])
        ax.loglog(r["lat"], r["j"], marker=mk, color=BATCH_COLOR[b],
                  ms=8.0, ls="none", alpha=0.9, mew=0.8,
                  markerfacecolor="none" if b == 16 else BATCH_COLOR[b])
    bl = sub.loc[sub["lat"].idxmin()]
    be = sub.loc[sub["j"].idxmin()]
    ax.scatter(bl["lat"], bl["j"], marker="o", s=180, facecolor="none",
               edgecolor="black", lw=1.6, zorder=5)
    if stack_key(bl) != stack_key(be):
        ax.scatter(be["lat"], be["j"], marker="s", s=180, facecolor="none",
                   edgecolor="black", lw=1.6, zorder=5)
    style_ax(ax)
    plain_ticks(ax)
    ax.set_title(MODEL_LABEL[model], fontsize=12)
    ax.set_xlabel("latency (ms / batch call)", fontsize=10, labelpad=3)
    ax.set_ylabel("J / batch call, gross", fontsize=10, labelpad=6)
    fig.tight_layout()
    save(fig, f"exp_scan_scatter_{model}")


def ort_opt_figure(agg):
    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    levels = [0, 1, 2, 99]
    xcat = np.arange(len(levels))
    for model in MODELS:
        for b in (1, 16):
            s = agg[(agg["model"] == model) & (agg["batch"] == b) &
                    (agg["backend"] == "ort-cuda")].copy()
            s["gl"] = s["graph_opt_level"].astype(float)
            base = s.loc[s["gl"] == float(levels[0]), "j"].iloc[0]
            rel = [s.loc[s["gl"] == float(lev), "j"].iloc[0] / base
                   for lev in levels]
            ax.plot(xcat, rel, marker="o", ms=6, lw=1.6,
                    color=MODEL_COLOR[model],
                    ls="-" if b == 1 else "--")
    ax.axhline(1.0, color="grey", lw=0.8, ls=":")
    ax.set_xticks(xcat)
    ax.set_xticklabels(["disable", "basic", "extended", "all"],
                       fontsize=8, rotation=22, ha="right")
    style_ax(ax)
    ax.set_xlabel("ORT graph optimization level", fontsize=10, labelpad=3)
    ax.set_ylabel("relative J/inf (disable = 1)", fontsize=10, labelpad=5)
    ax.set_title("Graph-opt level is not a free lunch", fontsize=11)
    ax.text(0.02, 0.97, "solid: batch 1\ndash: batch 16",
            transform=ax.transAxes, fontsize=7.5, va="top")
    fig.tight_layout()
    save(fig, "exp_scan_ort_opt")


def batch_figure(agg):
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    xpos = np.arange(6)
    labels = ["MN2\nORT", "MN2\neFP16", "RN50\nORT", "RN50\neFP16",
              "ViT\nORT", "ViT\neFP16"]
    w = 0.34
    pairs = [("mobilenetv2", "ort"), ("mobilenetv2", "eager"),
             ("resnet50", "ort"), ("resnet50", "eager"),
             ("vit_b_16", "ort"), ("vit_b_16", "eager")]
    for k, (model, kind) in enumerate(pairs):
        if kind == "ort":
            s = agg[(agg["model"] == model) & (agg["backend"] == "ort-cuda") &
                    (agg["graph_opt_level"] == 2)]
        else:
            s = agg[(agg["model"] == model) & (agg["backend"] == "torch-eager") &
                    (agg["precision"] == "fp16")]
        by_batch = {int(r["batch"]): r["j_per_img"] for _, r in s.iterrows()}
        ax.bar(xpos[k] - w / 2, by_batch.get(1), w, color=BATCH_COLOR[1], log=True)
        ax.bar(xpos[k] + w / 2, by_batch.get(16), w, color=BATCH_COLOR[16], log=True)
    ax.set_xticks(xpos)
    ax.set_xticklabels(labels, fontsize=8)
    ax.grid(axis="y", which="both", ls=":", lw=0.3, alpha=0.4)
    ax.tick_params(labelsize=9)
    ax.set_ylabel("J per image, gross", fontsize=10, labelpad=5)
    ax.set_title("Batching amortizes per-image energy", fontsize=11)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BATCH_COLOR[b])
                       for b in (1, 16)],
              labels=["batch 1", "batch 16"], fontsize=9, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=2)
    fig.tight_layout()
    save(fig, "exp_scan_batch")


def h2_figure(agg):
    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    offset = {
        ("mobilenetv2", 16): (1.8, 1.8, "left", "bottom"),
        ("resnet50", 1): (1.8, 1.8, "left", "bottom"),
        ("resnet50", 16): (1.8, -2.2, "left", "top"),
        ("vit_b_16", 1): (1.8, 1.8, "left", "bottom"),
    }
    for model in MODELS:
        for b in (1, 16):
            s = agg[(agg["model"] == model) & (agg["batch"] == b)]
            bl = s.loc[s["lat"].idxmin()]
            be = s.loc[s["j"].idxmin()]
            if stack_key(bl) == stack_key(be):
                ax.scatter(0, 0, color=MODEL_COLOR[model], s=20,
                           edgecolors="grey", linewidths=0.4, zorder=3)
                continue
            lat_pen = (bl["lat"] / be["lat"] - 1.0) * 100
            eng_sav = (1.0 - be["j"] / bl["j"]) * 100
            edp_energy = be["edp"] < bl["edp"]
            ax.scatter(lat_pen, eng_sav, color=MODEL_COLOR[model],
                       marker="*" if edp_energy else "o", s=55,
                       edgecolors="k", linewidths=0.4, zorder=3)
            dx, dy, ha, va = offset.get((model, b), (2, 2, "left", "bottom"))
            ax.annotate(f"{MODEL_LABEL[model]} b{b}",
                        xy=(lat_pen, eng_sav),
                        xytext=(lat_pen + dx, eng_sav + dy), fontsize=8,
                        ha=ha, va=va)
    ax.axhline(0, color="grey", lw=0.7)
    ax.axvline(0, color="grey", lw=0.7)
    ax.margins(0.16, 0.16)
    style_ax(ax)
    ax.set_xlabel("latency penalty of E-opt config (%)", fontsize=10, labelpad=3)
    ax.set_ylabel("energy saving of E-opt config (%)", fontsize=10, labelpad=5)
    ax.set_title("H2 divergence: penalty vs. saving", fontsize=11)
    fig.tight_layout()
    save(fig, "exp_scan_h2_v2")


def main():
    agg = load_agg()
    only = sys.argv[1:]  # optional: subset of scatter_* / ort_opt / batch / h2
    jobs = []
    if not only or any("scatter" in x for x in only):
        for model in MODELS:
            if not only or f"scatter_{model}" in only or any(
                    x == "scatter" for x in only):
                jobs.append(("scatter", model))
    if not only or "ort_opt" in only:
        jobs.append(("ort_opt", None))
    if not only or "batch" in only:
        jobs.append(("batch", None))
    if not only or "h2" in only:
        jobs.append(("h2", None))
    for kind, model in jobs:
        if kind == "scatter":
            scatter_figure(model, agg)
        elif kind == "ort_opt":
            ort_opt_figure(agg)
        elif kind == "batch":
            batch_figure(agg)
        elif kind == "h2":
            h2_figure(agg)


if __name__ == "__main__":
    main()
