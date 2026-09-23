# -*- coding: utf-8 -*-
"""Redraw the mini-experiment figure from the 36-config scan dataset.

One log-log panel per model; x = mean latency per batch call (ms),
y = mean J/inference gross (J per batch call). Markers:
  ORT graph-opt disable/basic/extended/all = v/^/s/o,
  torch eager fp32/fp16 = D/P; colour = batch 1 (blue) / 16 (orange).
Best-latency and best-energy points are annotated per panel.
"""
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(os.environ.get("TEMP", "/tmp")) / "mplcache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


BASE = Path(__file__).resolve().parent
RAW = BASE / "scan_out_20260908_012226_v2" / "scan_out_20260908_012226" \
    / "results_scan.csv"
OUT_PDF = BASE.parent / "Figures" / "experiment_scan_v2.pdf"
OUT_PNG = BASE.parent / "Figures" / "experiment_scan_v2.png"

MODELS = ["mobilenetv2", "resnet50", "vit_b_16"]
MODEL_LABEL = {
    "mobilenetv2": "MobileNetV2",
    "resnet50": "ResNet-50",
    "vit_b_16": "ViT-B/16",
}


def cfg_style(row):
    if row["backend"] == "ort-cuda":
        return {"opt": int(row["graph_opt_level"])}
    return {"eager": row["precision"]}


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
    )
    agg["batch"] = agg["batch"].astype(int)

    fig, axes = plt.subplots(1, 3, figsize=(11.6, 3.0), sharey=True)
    mark = {0: "v", 1: "^", 2: "s", 99: "o"}
    colors = {1: "#1f77b4", 16: "#ff7f0e"}
    handles, labels = [], []

    for ax, model in zip(axes, MODELS):
        sub = agg[agg["model"] == model]
        for _, r in sub.iterrows():
            if r["backend"] == "ort-cuda":
                m = mark[int(r["graph_opt_level"])]
                lab = f"ORT opt{int(r['graph_opt_level'])}"
            else:
                m = "D" if r["precision"] == "fp32" else "P"
                lab = f"eager {r['precision'].upper()}"
            c = colors[int(r["batch"])]
            (sc,) = ax.loglog(r["lat"], r["j"], marker=m, color=c, ms=5.5,
                              ls="none", mew=0.6, alpha=0.95)
            handles.append(sc)
            labels.append(f"{lab}, b{r['batch']}")

        # highlight latency-opt and energy-opt within this model
        bl = sub.loc[sub["lat"].idxmin()]
        be = sub.loc[sub["j"].idxmin()]
        for pt, tag, dy in ((bl, "lat-opt", 1.25), (be, "E-opt", 0.8)):
            ax.annotate(
                tag,
                xy=(pt["lat"], pt["j"]),
                xytext=(pt["lat"], pt["j"] * dy),
                fontsize=6.5,
                ha="center",
                color="#333333",
            )
        ax.set_title(MODEL_LABEL[model], fontsize=9)
        ax.set_xlabel("latency (ms / batch)", fontsize=8)
        ax.grid(which="both", ls=":", lw=0.3, alpha=0.4)
        ax.tick_params(labelsize=7)

    axes[0].set_ylabel("J / batch call (gross)", fontsize=8)
    fig.legend(
        handles, labels, loc="center left", bbox_to_anchor=(0.995, 0.5),
        fontsize=6.2, frameon=False, handletextpad=0.2, labelspacing=0.3,
        title="config",
    )
    fig.tight_layout(rect=(0, 0, 0.90, 1))
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PDF, dpi=300)
    fig.savefig(OUT_PNG, dpi=300)
    print("saved", OUT_PDF, OUT_PNG)

    # Console sanity: best latency/energy per (model, batch)
    for model in MODELS:
        for b in (1, 16):
            s = agg[(agg["model"] == model) & (agg["batch"] == b)]
            if len(s) < 2:
                continue
            bl = s.loc[s["lat"].idxmin()]
            be = s.loc[s["j"].idxmin()]
            div = "YES" if (bl[["backend", "precision", "graph_opt_level"]].tolist()
                            != be[["backend", "precision", "graph_opt_level"]].tolist()) else "no"
            print(f"{model} b{b}: lat-opt {bl['backend']}/{bl['precision']}/opt{bl['graph_opt_level']} "
                  f"{bl['lat']:.4f} | E-opt {be['backend']}/{be['precision']}/opt{be['graph_opt_level']} "
                  f"{be['j']:.6f} | divergent={div}")


if __name__ == "__main__":
    main()
