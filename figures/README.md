# Figure sources and generators / 图源与生成脚本

## English

Editable sources and generator scripts for the figures whose construction is
data-driven or diagrammatic. The remaining figures are plotted directly from the
experiment data and live in `experiment/scripts/`.

| File | Role |
|---|---|
| `PRISMA.drawio` | Editable source of the screening flow diagram (open with draw.io / diagrams.net) |
| `scripts/make_prisma_chart.py`, `scripts/prisma_layout.py` | Vector re-rendering of the same geometry, used to regenerate the draw.io source |
| `scripts/make_prisma_drawio.py` | Regenerates `PRISMA.drawio` from `prisma_layout.py`; this overwrites manual edits, use with care |
| `scripts/trim_pdf_margins.py` | Removes the white margin that draw.io leaves around exported pages |
| `scripts/render_drawio.py` | Renders a `.drawio` file to a single-page PDF and reports text that overflows its box |
| `scripts/make_category_chart_v2.py` | Ten-category distribution (Figure 3) |
| `scripts/make_energy_ops_chart.py` | Relative energy magnitude of operations (Figure 5) |
| `scripts/make_matrix_view_proposal.py` | Matrix view of the organising skeleton |

The exported PDF is scaled to the column width by LaTeX, so a tighter export
page yields a larger effective font size in the printed figure.

## 中文

本目录保存几何驱动或示意类图形的可编辑源与生成脚本。其余图形直接由实验数据绘制，
脚本在 `experiment/scripts/`。

| 文件 | 作用 |
|---|---|
| `PRISMA.drawio` | 文献筛选流程图的可编辑源（用 draw.io / diagrams.net 打开） |
| `scripts/make_prisma_chart.py`、`prisma_layout.py` | 同一套几何的矢量重绘，用于再生成 draw.io 源 |
| `scripts/make_prisma_drawio.py` | 由 `prisma_layout.py` 重新生成 `PRISMA.drawio`；会覆盖手工调整，慎用 |
| `scripts/trim_pdf_margins.py` | 裁掉 draw.io 导出页面四周的白边 |
| `scripts/render_drawio.py` | 把 `.drawio` 渲染为单页 PDF，并报告文字是否超出所属盒子 |
| `scripts/make_category_chart_v2.py` | 十类分布图（图 3） |
| `scripts/make_energy_ops_chart.py` | 各操作的相对能耗量级图（图 5） |
| `scripts/make_matrix_view_proposal.py` | 组织骨架的矩阵视图 |

导出的 PDF 由 LaTeX 按栏宽缩放，因此导出页面越紧凑，图内等效字号越大。
