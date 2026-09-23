# -*- coding: utf-8 -*-
"""Aggregate results_scan.csv into summary_scan.md and results_scan_agg.csv."""
import argparse
import csv
import statistics
import sys
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


def fmt(v, nd=4):
    return "" if v == "" or v is None else f"{v:.{nd}f}"


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def group_key(r):
    return (r.get("model", "?"), r.get("backend", "?"), r.get("precision", "?"),
            r.get("batch", "?"), r.get("graph_opt_level", "?"),
            r.get("intra_op_threads", "?"))


def label(key):
    model, backend, prec, batch, opt, thr = key
    if backend == "ort-cuda":
        optname = {0: "disable", 1: "basic", 2: "extended", 99: "all"}.get(int(opt), opt)
        return f"{model} | ORT-CUDA | {prec} | b{batch} | opt={optname}"
    if backend == "torch-compile":
        return f"{model} | torch.compile | {prec} | b{batch}"
    return f"{model} | {backend} | {prec} | b{batch}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default="summary_scan.md")
    ap.add_argument("--agg", default="results_scan_agg.csv")
    ap.add_argument("--failures", default=None)
    args = ap.parse_args()

    rows = load_rows(args.csv)
    if not rows:
        print("empty results")
        return 1

    groups = {}
    for r in rows:
        groups.setdefault(group_key(r), []).append(r)

    agg_rows = []
    lines = [
        "# 编译决策空间扫描汇总", "",
        "> 每(模型,后端,精度,batch,图优化)含多次重复(rep)，下表为跨重复均值±std。",
        "> 能耗口径：J/inf(总)含静态；J/inf(净)扣除 idle；一个推理单元=一次 batch 调用。",
        "> static% = idle/平均功耗。", "",
        "| model | backend | prec | batch | opt | lat_ms | p95_ms | qps | P_w | idle_w | J/inf(总) | J/inf(净) | EDP | static% |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key, reps in sorted(groups.items()):
        lat_m, lat_s = mean_std([fnum(r.get("mean_lat_ms")) for r in reps])
        p95_m, _ = mean_std([fnum(r.get("p95_lat_ms")) for r in reps])
        qps_m, _ = mean_std([fnum(r.get("throughput_qps")) for r in reps])
        pw_m, _ = mean_std([fnum(r.get("mean_power_w")) for r in reps])
        idle_m, _ = mean_std([fnum(r.get("idle_power_w")) for r in reps])
        ej_m, ej_s = mean_std([fnum(r.get("energy_j_per_inf")) for r in reps])
        ejn_m, _ = mean_std([fnum(r.get("energy_net_j_per_inf")) for r in reps])
        edp_m, _ = mean_std([fnum(r.get("edp")) for r in reps])
        st_m, _ = mean_std([fnum(r.get("static_share_pct")) for r in reps])
        model, backend, prec, batch, opt, thr = key
        lat_str = f"{fmt(lat_m, 3)} ± {fmt(lat_s, 3)}"
        ej_str = f"{fmt(ej_m, 6)} ± {fmt(ej_s, 6)}"
        line = (f"| {label(key).split(' | ')[0]} | {backend} | {prec} | b{batch} | "
                f"{opt if backend == 'ort-cuda' else '-'} | {lat_str} | {fmt(p95_m, 3)} | "
                f"{fmt(qps_m, 1)} | {fmt(pw_m, 2)} | {fmt(idle_m, 2)} | {ej_str} | "
                f"{fmt(ejn_m, 6)} | {fmt(edp_m, 9)} | {fmt(st_m, 1)} |")
        lines.append(line)
        agg_rows.append({
            "model": model, "backend": backend, "precision": prec, "batch": batch,
            "graph_opt_level": opt, "intra_op_threads": thr,
            "lat_ms_mean": fmt(lat_m, 4), "lat_ms_std": fmt(lat_s, 4),
            "p95_ms": fmt(p95_m, 4), "qps": fmt(qps_m, 2),
            "power_w": fmt(pw_m, 2), "idle_w": fmt(idle_m, 2),
            "j_inf_gross": fmt(ej_m, 6), "j_inf_net": fmt(ejn_m, 6),
            "edp": fmt(edp_m, 9), "static_share_pct": fmt(st_m, 1),
        })

    # H2 style check per (model, batch): best latency vs best energy gross
    lines += ["", "## 延迟最优 vs 能耗最优（跨配置，按模型×batch）", ""]
    for model in sorted({k[0] for k in groups}):
        for batch in sorted({k[3] for k in groups if k[0] == model}):
            items = []
            for key, reps in groups.items():
                if key[0] != model or key[3] != batch:
                    continue
                lat_m, _ = mean_std([fnum(r.get("mean_lat_ms")) for r in reps])
                ej_m, _ = mean_std([fnum(r.get("energy_j_per_inf")) for r in reps])
                if lat_m != "" and ej_m != "":
                    items.append((label(key), lat_m, ej_m))
            if len(items) < 2:
                continue
            best_lat = min(items, key=lambda it: it[1])
            best_eng = min(items, key=lambda it: it[2])
            h2 = "支持(延迟最优≠能耗最优)" if best_lat[0] != best_eng[0] else "未观察到"
            lines.append(f"- {model} b{batch}: 延迟最优={best_lat[0]}，能耗最优={best_eng[0]} → H2 {h2}")

    # Compiler-decision spread per (model, batch) among ORT opt levels
    lines += ["", "## ORT 图优化等级对 J/inf 的影响（模型×batch 内跨 opt 极差）", ""]
    for model in sorted({k[0] for k in groups}):
        for batch in sorted({k[3] for k in groups if k[0] == model}):
            vals = []
            for key, reps in groups.items():
                if key[0] == model and key[1] == "ort-cuda" and key[3] == batch:
                    ej_m, _ = mean_std([fnum(r.get("energy_j_per_inf")) for r in reps])
                    if ej_m != "":
                        vals.append((key[4], ej_m))
            if len(vals) >= 2:
                lo = min(v for _, v in vals)
                hi = max(v for _, v in vals)
                lines.append(f"- {model} b{batch}: ORT J/inf 跨 4 档图优化从 {lo:.6f} 到 {hi:.6f} J "
                             f"（{(hi - lo) / lo * 100:.1f}% 相对极差）")

    if args.failures and Path(args.failures).exists():
        lines += ["", "## 失败/跳过配置", ""]
        lines.append("```text")
        lines.extend(Path(args.failures).read_text(encoding="utf-8").splitlines())
        lines.append("```")

    lines += ["", "> DRAM 字节计数仍受平台权限限制时，本节以延迟/J/inf/EDP 的相对变化为口径。"]
    text = "\n".join(lines) + "\n"
    Path(args.out).write_text(text, encoding="utf-8")
    if agg_rows:
        with open(args.agg, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(agg_rows[0].keys()))
            w.writeheader()
            w.writerows(agg_rows)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
