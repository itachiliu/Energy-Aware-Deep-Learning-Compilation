# -*- coding: utf-8 -*-
"""Batch-2 figures (RTX 4090, x86) plus the A100-vs-4090 comparison.

Reads the *aggregated* scan CSVs, so it still works when only
results_scan_agg.csv survived a transfer. Writes PDF and PNG into <repo>/Figures.

    ~/dlxvenv/bin/python job/plot_x86_batch.py
"""
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
import pandas as pd

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "axes.unicode_minus": False,
})

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
FIG_DIR = ROOT.parent / "Figures"

def pick(*candidates):
    """Prefer the raw per-repetition CSV, fall back to the aggregated one."""
    for cand in candidates:
        if Path(cand).exists():
            return Path(cand)
    return Path(candidates[0])


B2 = pick(
    ROOT / "scan_x86_out_20260914_163144_full" / "scan_x86_out_20260914_163144"
    / "results_scan.csv",
    ROOT / "scan_x86_out_20260914_163144" / "scan_x86_out_20260914_163144"
    / "results_scan_agg.csv",
)
B1 = pick(
    ROOT / "scan_out_20260908_012226_v2" / "results_scan.csv",
    ROOT / "scan_out_20260908_012226_v2" / "results_scan_agg_v2.csv",
)

# Ordered by approximate FLOPs so the panels read small-to-large.
GFLOPS = {"mobilenetv2": 0.31, "mobilenetv3_large": 0.44, "resnet18": 1.8,
          "resnet50": 4.1, "vit_b_16": 17.6}
MODEL_LABEL = {"mobilenetv2": "MobileNetV2", "mobilenetv3_large": "MobileNetV3-L",
               "resnet18": "ResNet-18", "resnet50": "ResNet-50",
               "vit_b_16": "ViT-B/16"}
MODEL_COLOR = {"mobilenetv2": "#1f77b4", "mobilenetv3_large": "#17becf",
               "resnet18": "#9467bd", "resnet50": "#d62728",
               "vit_b_16": "#2ca02c"}
BATCH_COLOR = {1: "#1f77b4", 16: "#ff7f0e"}
LEVEL_NAME = {0: "disable", 1: "basic", 2: "extended", 99: "all"}
MARKS = {"ORT disable": "v", "ORT basic": "^", "ORT extended": "s",
         "ORT all": "o", "eager FP32": "D", "eager FP16": "P",
         "compile FP32": "X", "compile FP16": "*"}


def stack_label(row):
    backend, prec = row["backend"], row["precision"]
    if backend == "ort-cuda":
        level = int(float(row["graph_opt_level"]))
        return "ORT " + LEVEL_NAME.get(level, str(level))
    if backend == "torch-eager":
        return "eager " + str(prec).upper()
    if backend == "torch-compile":
        return "compile " + str(prec).upper()
    return str(backend)


def load(path):
    df = pd.read_csv(path)
    df = df.rename(columns={
        # aggregated schema
        "lat_ms": "lat", "lat_ms_mean": "lat",
        "power_w": "power", "idle_w": "idle",
        "j_inf_gross": "j", "j_inf_net": "j_net", "p95_ms": "p95",
        # raw per-repetition schema
        "mean_lat_ms": "lat", "mean_power_w": "power",
        "idle_power_w": "idle", "energy_j_per_inf": "j",
        "energy_net_j_per_inf": "j_net", "p95_lat_ms": "p95",
    })
    df["batch"] = df["batch"].astype(int)
    df["j"] = pd.to_numeric(df["j"], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["power"] = pd.to_numeric(df["power"], errors="coerce")
    df["idle"] = pd.to_numeric(df["idle"], errors="coerce")
    df["p95"] = pd.to_numeric(df["p95"], errors="coerce")
    df["graph_opt_level"] = pd.to_numeric(df["graph_opt_level"], errors="coerce")
    # Raw files carry one row per repetition; collapse to one row per config.
    df = df.groupby(
        ["model", "backend", "precision", "batch", "graph_opt_level"],
        as_index=False, dropna=False,
    ).agg(lat=("lat", "mean"), j=("j", "mean"), power=("power", "mean"),
          idle=("idle", "mean"), p95=("p95", "mean"))
    df["j_per_img"] = df["j"] / df["batch"]
    df["static"] = df["idle"] / df["power"] * 100.0
    df["stack"] = df.apply(stack_label, axis=1)
    return df


def save(fig, stem):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / (stem + ".pdf"), dpi=300)
    fig.savefig(FIG_DIR / (stem + ".png"), dpi=300)
    plt.close(fig)
    print("saved", FIG_DIR / (stem + ".pdf"))


def style_ax(ax):
    ax.grid(which="both", ls=":", lw=0.3, alpha=0.4)
    ax.tick_params(labelsize=9)


def plain_ticks(ax, xs, ys):
    ax.set_xticks(xs)
    ax.set_xticklabels(["{:g}".format(v) for v in xs])
    ax.set_yticks(ys)
    ax.set_yticklabels(["{:g}".format(v) for v in ys])
    ax.tick_params(which="minor", labelbottom=False, labelleft=False)


def scatter_figure(model, df):
    sub = df[df["model"] == model]
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    for b in (1, 16):
        ort = sub[(sub["backend"] == "ort-cuda") & (sub["batch"] == b)]
        ort = ort.sort_values("graph_opt_level")
        ax.plot(ort["lat"], ort["j"], ls="-", color="grey", lw=1.0,
                alpha=0.55, zorder=1)
    for _, r in sub.iterrows():
        mk = MARKS.get(r["stack"], "o")
        b = int(r["batch"])
        ax.loglog(r["lat"], r["j"], marker=mk, color=BATCH_COLOR[b],
                  ms=8.5, ls="none", alpha=0.9, mew=0.9,
                  markerfacecolor="none" if b == 16 else BATCH_COLOR[b])
    best_lat = sub.loc[sub["lat"].idxmin()]
    best_j = sub.loc[sub["j"].idxmin()]
    ax.scatter(best_lat["lat"], best_lat["j"], marker="o", s=210,
               facecolor="none", edgecolor="black", lw=1.5, zorder=5)
    if best_lat["stack"] != best_j["stack"] or best_lat["batch"] != best_j["batch"]:
        ax.scatter(best_j["lat"], best_j["j"], marker="s", s=210,
                   facecolor="none", edgecolor="black", lw=1.5, zorder=5)
    style_ax(ax)
    ax.set_xlim(sub["lat"].min() * 0.75, sub["lat"].max() * 1.3)
    ax.set_ylim(sub["j"].min() * 0.75, sub["j"].max() * 1.35)
    plain_ticks(ax, [1, 2, 3, 5, 10, 20], [0.1, 0.2, 0.5, 1, 2, 5, 10])
    ax.set_title(MODEL_LABEL[model], fontsize=12)
    ax.set_xlabel("latency (ms / batch call)", fontsize=10, labelpad=3)
    ax.set_ylabel("J / batch call, gross", fontsize=10, labelpad=6)
    fig.tight_layout()
    save(fig, "exp_x86_scatter_" + model)


def ort_opt_figure(df, models):
    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    levels = [0, 1, 2, 99]
    xcat = np.arange(len(levels))
    for model in models:
        for b in (1, 16):
            s = df[(df["model"] == model) & (df["batch"] == b) &
                   (df["backend"] == "ort-cuda")].copy()
            s = s.dropna(subset=["graph_opt_level"]).sort_values("graph_opt_level")
            if len(s) < 2:
                continue
            base = float(s["j"].iloc[0])
            rel = [float(v) / base for v in s["j"]]
            ax.plot(xcat[:len(rel)], rel, marker="o", ms=6, lw=1.6,
                    color=MODEL_COLOR[model], ls="-" if b == 1 else "--")
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
    save(fig, "exp_x86_ort_opt")


def spread_figure(df, models):
    fig, ax = plt.subplots(figsize=(5.8, 1.4 + 0.42 * len(models) * 2))
    order = ["ORT", "eager FP32", "eager FP16", "compile FP32", "compile FP16"]
    ypos = np.arange(len(models) * 2)
    ylabels = []
    k = 0
    for model in models:
        for b in (1, 16):
            ylabels.append("{}\nb{}".format(MODEL_LABEL[model], b))
            sub = df[(df["model"] == model) & (df["batch"] == b)]
            vals = []
            for name in order:
                if name == "ORT":
                    s = sub[sub["backend"] == "ort-cuda"]
                else:
                    backend, prec = name.split()
                    backend = "torch-" + backend
                    s = sub[(sub["backend"] == backend) &
                            (sub["precision"] == prec.lower())]
                vals.append(float(s["j"].min()) if len(s) else np.nan)
            lo = np.nanmin(vals)
            ax.barh(k, lo, height=0.62, color="#4c72b0", alpha=0.95)
            ax.barh(k, np.nanmax(vals) - lo, left=lo, height=0.62,
                    color="#c44e52", alpha=0.30)
            ax.plot(vals, [k] * len(vals), ls="none", marker="o", ms=5,
                    color="black", zorder=4)
            spread = (np.nanmax(vals) - lo) / lo * 100.0
            ax.text(np.nanmax(vals) * 1.04, k, "{:.0f}%".format(spread),
                    va="center", fontsize=8.5)
            k += 1
    ax.set_yticks(ypos)
    ax.set_yticklabels(ylabels, fontsize=8)
    ax.invert_yaxis()
    style_ax(ax)
    ax.set_xlabel("J / batch call (gross); dot = each stack's best", fontsize=9.5)
    ax.set_title("Same model, same batch, different stack", fontsize=11)
    ax.set_xlim(0, 9.6)
    fig.tight_layout()
    save(fig, "exp_x86_backend_spread")


def crossgpu_figure(b1, b2, models):
    rows = []
    for model in models:
        for batch in (1, 16):
            a = b1[(b1["model"] == model) & (b1["batch"] == batch) &
                   (b1["backend"] == "ort-cuda") & (b1["precision"] == "fp32")]
            b = b2[(b2["model"] == model) & (b2["batch"] == batch) &
                   (b2["backend"] == "ort-cuda") & (b2["precision"] == "fp32")]
            if not len(a) or not len(b):
                continue
            rows.append((model, batch,
                         float(b["lat"].mean()) / float(a["lat"].mean()),
                         float(b["j"].mean()) / float(a["j"].mean())))
    fig, ax = plt.subplots(figsize=(5.8, 3.6))
    ypos = np.arange(len(rows))
    w = 0.36
    lat = [r[2] for r in rows]
    eng = [r[3] for r in rows]
    ax.barh(ypos - w / 2, lat, height=w, color="#4c72b0", label="latency ratio")
    ax.barh(ypos + w / 2, eng, height=w, color="#dd8452", label="J/inf ratio")
    ax.axvline(1.0, color="black", lw=0.9, ls="--")
    ax.set_yticks(ypos)
    ax.set_yticklabels(["{}\nb{}".format(MODEL_LABEL[r[0]], r[1]) for r in rows],
                       fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, max(max(lat), max(eng)) * 1.3)
    style_ax(ax)
    ax.set_xlabel("RTX 4090 / A100-PCIe ratio (same config, ORT-CUDA fp32)",
                  fontsize=9.5)
    ax.set_title("<1 means the 4090 wins; the two metrics disagree",
                 fontsize=11)
    ax.legend(fontsize=8.5, loc="upper right")
    fig.tight_layout()
    save(fig, "exp_x86_crossgpu")


def main():
    missing = [str(p) for p in (B2, B1) if not p.exists()]
    if missing:
        for m in missing:
            print("missing:", m)
        return 1
    df2 = load(B2)
    df1 = load(B1)
    models2 = sorted({m for m in df2["model"]}, key=lambda m: GFLOPS.get(m, 99))
    models1 = sorted({m for m in df1["model"]}, key=lambda m: GFLOPS.get(m, 99))
    print("batch-2 configs:", len(df2), " batch-1 configs:", len(df1))
    print("batch-2 models:", ", ".join(models2))
    for model in models2:
        scatter_figure(model, df2)
    ort_opt_figure(df2, models2)
    spread_figure(df2, models2)
    crossgpu_figure(df1, df2, [m for m in models2 if m in set(models1)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
