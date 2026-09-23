# -*- coding: utf-8 -*-
"""Aggregate results.csv (one row per repetition) into a Markdown summary."""
import argparse
import csv
import statistics
from pathlib import Path


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def mean_std(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "", ""
    m = statistics.mean(vals)
    s = statistics.stdev(vals) if len(vals) > 1 else 0.0
    return m, s


def fmt(v, nd=4, unit=""):
    if v is None or v == "":
        return ""
    return f"{v:.{nd}f}{unit}"


def fmt_ms(v):
    if v is None or v == "":
        return ""
    return f"{v:.3f}"


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="summary.md")
    ap.add_argument("--failures", default=None)
    args = ap.parse_args()

    rows = load_rows(args.csv)
    if not rows:
        print("empty results")
        return 1

    groups = {}
    for r in rows:
        key = (r.get("model", "?"), r.get("backend", "?"), r.get("precision", "?"))
        groups.setdefault(key, []).append(r)

    lines = [
        "# 最小验证实验汇总（多后端版）", "",
        "> 每(模型,后端,精度)含多次重复（rep）；下表为跨重复均值。能耗口径：",
        "> J/inf(总) 含静态；J/inf(净) 扣除 idle 功耗。",
        "",
        "| model | backend | precision | GFLOPs~ | lat_ms(mean±std) | p95_ms | qps | P_w | idle_w | J/inf(总) | J/inf(净) | EDP |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for (model, backend, prec), reps in sorted(groups.items()):
        flops = fnum(reps[0].get("flops_approx_g"))
        lat_m, lat_s = mean_std([fnum(r.get("mean_lat_ms")) for r in reps])
        p95_m, _ = mean_std([fnum(r.get("p95_lat_ms")) for r in reps])
        qps_m, _ = mean_std([fnum(r.get("throughput_qps")) for r in reps])
        pw_m, _ = mean_std([fnum(r.get("mean_power_w")) for r in reps])
        idle_m, _ = mean_std([fnum(r.get("idle_power_w")) for r in reps])
        ej_m, ej_s = mean_std([fnum(r.get("energy_j_per_inf")) for r in reps])
        ejn_m, _ = mean_std([fnum(r.get("energy_net_j_per_inf")) for r in reps])
        edp_m, _ = mean_std([fnum(r.get("edp")) for r in reps])
        lat_str = ""
        if lat_m != "":
            lat_str = f"{fmt_ms(lat_m)} ± {fmt_ms(lat_s)}"
        ej_str = ""
        if ej_m != "":
            ej_str = f"{ej_m:.6f}" + (f" ± {ej_s:.6f}" if ej_s != "" else "")
        lines.append(
            f"| {model} | {backend} | {prec} | {'' if flops is None else f'{flops:.2f}'} | "
            f"{lat_str} | {fmt_ms(p95_m)} | {fmt(qps_m, 1)} | {fmt(pw_m, 2)} | "
            f"{fmt(idle_m, 2)} | {ej_str} | {fmt(ejn_m, 6)} | {fmt(edp_m, 9)} |"
        )

    # H1/H2: per-model comparison across all measured configs
    lines += ["", "## H1/H2 快速检查（同模型跨后端/精度比较）", ""]
    for model in sorted({k[0] for k in groups}):
        items = []
        for (m, backend, prec), reps in groups.items():
            if m != model:
                continue
            lat_m, _ = mean_std([fnum(r.get("mean_lat_ms")) for r in reps])
            ej_m, _ = mean_std([fnum(r.get("energy_j_per_inf")) for r in reps])
            if lat_m != "" and ej_m != "":
                items.append((f"{backend}/{prec}", lat_m, ej_m))
        if len(items) < 2:
            continue
        best_lat = min(items, key=lambda it: it[1])
        best_eng = min(items, key=lambda it: it[2])
        h2 = "支持（延迟最优 ≠ 能耗最优）" if best_lat[0] != best_eng[0] else "未观察到（同一配置）"
        lines.append(f"- {model}: 延迟最优={best_lat[0]}，能耗最优={best_eng[0]} → H2 {h2}")

    lines += ["", "## H1 跨模型提示（人工核对）", ""]
    lines.append(
        "比较 MobileNetV2 / ResNet-50 / ViT-B/16 的 FLOPs 排序与各配置 J/inf 排序："
        "若不一致（如 FLOPs 最低者并非 J/inf 最低），即为 H1 的直接证据。"
    )

    if args.failures and Path(args.failures).exists():
        lines += ["", "## 失败/跳过配置", ""]
        lines.append("```text")
        lines.extend(Path(args.failures).read_text(encoding="utf-8").splitlines())
        lines.append("```")

    lines += ["", "> DRAM 字节数未采集（平台未授予 Nsight Compute 权限时）。"]
    text = "\n".join(lines) + "\n"
    Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    main()
