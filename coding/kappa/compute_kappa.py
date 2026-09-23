#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复现包工具：由双人独立编码表计算 Cohen's kappa，并校验与正文报告值一致。

用法：
  1) 生成空模板（S01--S121，含两列空编码字段）：
       python compute_kappa.py --init-template coding_121.csv
  2) 人工填写 coding_121.csv（标题可留空或仅作人工核对）后：
       python compute_kappa.py --csv coding_121.csv
     可选参数：--expect-category 0.87 --expect-boundary 0.79

CSV 必需列（大小写不敏感）：
  sample_id, coder_a_category, coder_b_category,
  coder_a_boundary, coder_b_boundary

注意：本脚本只计算一致性，不判定正确性；正文已声明 Cohen's kappa 衡量的是
编码者间一致性而非编码正确性。原始编码表为作者持有材料，投稿时随复现包提供；
请勿伪造或事后修改独立编码阶段的记录。
"""
import argparse
import csv
import sys


def kappa(a, b):
    """Cohen's kappa for two lists of categorical labels."""
    if len(a) != len(b) or not a:
        return None
    n = float(len(a))
    classes = sorted(set(a) | set(b))
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = 0.0
    for c in classes:
        pe += (a.count(c) / n) * (b.count(c) / n)
    return (po - pe) / (1.0 - pe) if pe < 1.0 else None


def read_cols(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit("empty CSV")
    keys = {k.strip().lower(): k for k in rows[0].keys()}
    need = ["sample_id", "coder_a_category", "coder_b_category",
            "coder_a_boundary", "coder_b_boundary"]
    for n in need:
        if n not in keys:
            sys.exit(f"missing column: {n} (present: {sorted(keys)})")

    def col(name):
        return [str(r[keys[name]]).strip() for r in rows
                if str(r[keys[name]]).strip() != ""]

    a_cat, b_cat = col("coder_a_category"), col("coder_b_category")
    a_bnd, b_bnd = col("coder_a_boundary"), col("coder_b_boundary")
    return a_cat, b_cat, a_bnd, b_bnd


def write_template(path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "title", "coder_a_category", "coder_b_category",
                    "coder_a_boundary", "coder_b_boundary",
                    "final_category", "final_boundary", "dispute", "notes"])
        for i in range(1, 122):
            w.writerow([f"S{i:03d}", "", "", "", "", "", "", "", "", ""])
    print(f"template written: {path} (S01--S121)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="coding_121.csv")
    ap.add_argument("--init-template", metavar="OUT.csv")
    ap.add_argument("--expect-category", type=float, default=None)
    ap.add_argument("--expect-boundary", type=float, default=None)
    args = ap.parse_args()
    if args.init_template:
        write_template(args.init_template)
        return 0
    a_cat, b_cat, a_bnd, b_bnd = read_cols(args.csv)
    k_cat = kappa(a_cat, b_cat)
    k_bnd = kappa(a_bnd, b_bnd)
    print(f"N(category)={len(a_cat)}  kappa(category)={k_cat:.4f}" if k_cat is not None
          else "category labels insufficient")
    print(f"N(boundary)={len(a_bnd)}  kappa(boundary)={k_bnd:.4f}" if k_bnd is not None
          else "boundary labels insufficient")
    ok = True
    for name, val, exp in (("category", k_cat, args.expect_category),
                           ("boundary", k_bnd, args.expect_boundary)):
        if exp is not None and val is not None and abs(val - exp) > 1e-9:
            ok = False
            print(f"MISMATCH: {name} kappa={val:.4f} != expected {exp}")
    if args.expect_category is not None or args.expect_boundary is not None:
        print("check:", "OK" if ok else "FAILED")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
