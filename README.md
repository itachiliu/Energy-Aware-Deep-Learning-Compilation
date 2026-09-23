# Energy-Aware Deep Learning Compilation — Supplementary Material

Supporting material for the survey
**"A Survey of Energy-Aware Deep Learning Compilation: From Cost Models to
Production Compiler Stacks"** (Xincheng HE, Yan LIU).

The manuscript points to this repository as the home of its supplementary
material, under the short name "the supplementary repository". A four-page
index of the material is provided in both languages:

- English: [`docs/supplementary-material-en.pdf`](docs/supplementary-material-en.pdf)
- 中文：[`docs/supplementary-material-cn.pdf`](docs/supplementary-material-cn.pdf)

---

## 中文说明

本仓库是综述论文《面向能效的深度学习编译综述：从代价模型到生产级编译栈》的
支撑材料。正文中的补充材料指向本仓库（正文简称"配套 GitHub 仓库"），入口文档为
[`docs/supplementary-material-cn.pdf`](docs/supplementary-material-cn.pdf)（4 页索引）。

材料分六组：文献编码与一致性记录、独立抽查协议、4×4 矩阵计数、0/18 生态表证据、
检索与筛选计数，以及最小验证实验的原始数据与作业包。

仓库只保留正文引用的材料与复核结论所需的最小集合：中间工作稿、环境探测脚本、
未参与论文结果的纯 TensorRT 代码路径，以及被最终版本取代的早期编码轮次均未上传。
实验的 117 份逐次测量日志汇总为单个压缩包
`experiment/data/raw-measurement-logs.zip`，不再以 117 个散文件形式存放。
图形文件及其可编辑源随论文正文保存，不在本仓库重复存放。

---

## What is in this repository

| Path | What it contains | Where it supports the paper |
|---|---|---|
| `docs/` | Supplementary index document (PDF + LaTeX), Chinese and English | Every pointer to the supplementary repository |
| `coding/` | Two-coder coding of the 121 included studies, the controlled vocabularies, the disagreement list and the adjudication records | §II-F methodology; the Cohen's κ table; Appendix A |
| `coding/kappa/` | κ computation, reconciliation merge, appendix synchronisation scripts and their reports | §II-F; reproducibility of Appendix A |
| `audit/` | Rule-based historical coding, internal consistency audit, non-author spot-check protocol and sample | §II-F; the transparency statement |
| `matrix/` | The 4×4 granularity × mechanism counts, the empty-cell determination and the counting script | §I; §II-A; `tab:matrix-counts` |
| `ecosystem/` | Row-by-row evidence for the 18 production stacks and the 0/18 result, including excluded candidates | §II-D; Table 2 |
| `methodology/` | PRISMA stage counts and the post-window preprint tracking list | Figure 2; §II-E |
| `experiment/` | Protocol, per-scan result tables, the archived per-run measurement logs, the configuration matrix, the measurement pipeline and the plotting scripts of the small-scale validation experiment | §XIII; Tables 15–16; Figures 10–12 |

The repository keeps the material the paper points to together with the
artefacts needed to verify its claims. Intermediate working files, environment
probes, an unused TensorRT-only code path and the earlier coding rounds that the
final ones supersede are not shipped. The 117 per-run measurement logs of the
experiment are collected into a single archive,
`experiment/data/raw-measurement-logs.zip`, rather than 117 loose files.
Figures and their editable sources stay with the manuscript and are not
duplicated here.

## Key numbers in one place

- **121** included studies, assigned to **10** controlled categories.
- **0/18** production stacks write energy, power or EDP into the compile-time
  objective; the dedicated mapping/DSE control group is 6/6.
- **4×4** matrix over granularity × mechanism: Graph 20, Loop/Op 28,
  Placement 10, Power 10 (n = 68). Empty cells: Placement × Agentic and
  Power × Agentic.
- Two-coder Cohen's κ: category 0.77, granularity 0.66, mechanism 0.65,
  object type 0.85. 96 disagreeing units, all resolved through two
  reconciliation rounds and a third criterion-first adjudication round.
- Small-scale validation experiment: 36 runnable configurations on A100-PCIe,
  80 on RTX 4090, eight 20 s steady-state windows per configuration.

## How to re-run the analysis

```bash
# 4x4 matrix counts from the final coding
python matrix/count_matrix.py

# merge the reconciliation records into the final coding
python coding/kappa/merge_reconciliation.py

# push the final coding into Appendix A and its machine-readable mirror
python coding/kappa/sync_appendix_from_final.py --write

# check that the scope section, Appendix A and the counts agree
python audit/audit_scope_appendix_consistency.py
python audit/crosscheck_appendix.py

# optional non-author spot check
python audit/audit_coding.py
```

Scripts were run with Python 3.12. The LaTeX build needs XeLaTeX for the
Chinese documents and pdfLaTeX for the English ones.

## Language convention

The documentation in this repository is bilingual. The two supplementary index
documents are parallel translations. Data files, column headers and code
comments follow the language of the coding manual they implement; the controlled
vocabulary itself is Chinese in `coding/coding-rubric-v3.md` and mirrored in
English in the paper's Appendix A.

## Integrity statement

The first-round independent coding records are preserved unmodified. Later
reconciliation and adjudication steps are recorded in separate files and never
overwrite the original coder sheets. Empty cells and the 0/18 result are
supported by the documented evidence chains rather than by post-hoc rule
changes.

## Citation

If you use this material, please cite the survey. The BibTeX entry will be
added once the paper is published.

## Licence and scope

The data, documentation and scripts here are released under CC BY 4.0; see
[`LICENSE`](LICENSE).

The LaTeX sources of the manuscript itself are not included, because the paper
is under review. Three consistency scripts
(`audit/audit_scope_appendix_consistency.py`, `audit/crosscheck_appendix.py` and
`coding/kappa/sync_appendix_from_final.py`) read the manuscript files; they
expect them in a `manuscript/` directory next to this repository. Every other
script in the repository runs from the repository root without any external
input.

## 许可与范围

本仓库的数据、文档与脚本以 CC BY 4.0 许可发布，见 [`LICENSE`](LICENSE)。

论文正文的 LaTeX 源码未包含在本仓库中（论文仍在评审）。三个一致性脚本
（`audit/audit_scope_appendix_consistency.py`、`audit/crosscheck_appendix.py`
与 `coding/kappa/sync_appendix_from_final.py`）需要读取正文源文件，期望其在
本仓库同级的 `manuscript/` 目录下。仓库内其余脚本均可直接在仓库根目录运行，
不依赖外部输入。
