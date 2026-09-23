# Audit and independent spot check / 审计与非作者抽查

## English

Two kinds of audit are recorded here.

**Internal audit.** The single-coder, rule-based coding stage is kept as a
historical trace, together with the difference list against the final coding.
At that stage 23 of 121 rows were changed from the default rule by S-level
overrides; after two-coder independent coding replaced it, the number of rows on
which the same rule differs from the final coding rose to 87. This is the
evidence that rule-based coding cannot substitute for human judgement.

**Non-author spot check (optional).** A third party can fill the independent
columns of `coding-audit-sample30.csv` following `coding-audit-protocol.md`, then
run `audit_coding.py` to obtain the agreement rate and Cohen's κ. The sampled
30 items were selected by `coding-audit-sample30-selection.txt`.

| File | Role |
|---|---|
| `code_matrix.py`, `internal-audit.md` | Rule-based historical coding and its audit |
| `appendix-matrix-code.csv` | Machine-readable mirror of Appendix A, including the object-type column |
| `audit_internal.py`, `compute_audit30.py`, `audit30-report.txt` | Audit scripts and their reports |
| `coding-audit-protocol.md` | Protocol for an independent, non-author spot check |
| `coding-audit-sample30.csv`, `-blank.csv`, `-filled.csv`, `-selection.txt` | The 30-item sample, its blank form, the worked example and the selection log |
| `audit_coding.py` | Computes agreement and κ from the filled sample |
| `audit_scope_appendix_consistency.py`, `crosscheck_appendix.py` | Consistency checks binding the scope section, Appendix A and the machine-readable copy |

The two consistency checkers report `no inconsistencies found` and 0 mismatches.

## 中文

本目录记录两类审计。

**内部审计。** 单编码者阶段的规则式编码作为历史留痕保留，并附与最终编码的差异
清单。该阶段 121 行中有 23 行由 S 级覆盖改变默认规则；在两人独立编码取代它之后，
同一规则与最终编码的差异行数升至 87。这是"规则式编码无法替代人工判定"的证据。

**非作者抽查（可选）。** 第三方可按 `coding-audit-protocol.md` 填写
`coding-audit-sample30.csv` 的独立列，再运行 `audit_coding.py` 得到一致率与
Cohen's κ。30 条抽样由 `coding-audit-sample30-selection.txt` 记录。

| 文件 | 作用 |
|---|---|
| `code_matrix.py`、`internal-audit.md` | 规则式历史编码及其审计 |
| `appendix-matrix-code.csv` | 附录 A 的机器可读镜像（含对象类型列） |
| `audit_internal.py`、`compute_audit30.py`、`audit30-report.txt` | 审计脚本与报告 |
| `coding-audit-protocol.md` | 非作者独立抽查协议 |
| `coding-audit-sample30*.csv`、`-selection.txt` | 30 条抽样、空白表、示例与抽样说明 |
| `audit_coding.py` | 由填好的抽样表计算一致率与 κ |
| `audit_scope_appendix_consistency.py`、`crosscheck_appendix.py` | 范围界定、附录 A 与机器副本之间的一致性核对 |

两个一致性脚本分别报告 `no inconsistencies found` 与 0 处不匹配。
