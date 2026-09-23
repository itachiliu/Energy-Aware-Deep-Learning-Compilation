# -*- coding: utf-8 -*-
"""Cohen's kappa + agreement for the 30-row independent coding audit."""
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
CSV = ROOT / "coding-audit-sample30.csv"


def kappa(a, b):
    n = len(a)
    if n == 0:
        return None
    agree = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pa = sum((sum(1 for x in a if x == c) / n) *
             (sum(1 for y in b if y == c) / n) for c in cats)
    denom = 1 - pa
    return (agree - pa) / denom if denom else 1.0


def main():
    rows = []
    with open(CSV, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    pairs = [(r["HeuristicGranularity"], r["IndependentGranularity"],
              r["HeuristicMechanism"], r["IndependentMechanism"]) for r in rows]
    done = [p for p in pairs if p[1] and p[3]]
    print(f"rows={len(rows)} filled={len(done)}")
    if not done:
        print("independent columns are empty; fill them first")
        return 1
    g = [(p[0], p[1]) for p in done]
    m = [(p[2], p[3]) for p in done]
    for name, col in (("Granularity", g), ("Mechanism", m)):
        agree = sum(x == y for x, y in col) / len(col)
        k = kappa([x for x, _ in col], [y for _, y in col])
        print(f"{name}: agreement={agree:.3f} kappa={k:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
