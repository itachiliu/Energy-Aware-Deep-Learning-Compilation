# 附录 A 双编码独立复核协议（30 条抽样）

## 目的

为 121 行“粒度（Granularity）与机制（Mechanism）”编码提供一份非作者抽查，
以支撑正文“矩阵空格”结论的可复核性。

## 做法

1. 使用 `coding-audit-sample30.csv`（固定种子 20260909 抽取，30/121，不重复）。
2. 复核者**不查看** `HeuristicGranularity/HeuristicMechanism` 两列，独立填写
   `IndependentGranularity` 与 `IndependentMechanism`；可选填 `Disagreement` 备注。
3. 编码选项：
   - Granularity：Graph / Loop/Op / Placement / Power / Other
   - Mechanism：Analytical / Learned / AutoSearch / Agentic / Other
4. 回传后运行 `python supplements/audit_coding.py`，输出逐列一致率与 Cohen's $\kappa$。
5. 若 $\kappa<0.6$：作者逐条回看分歧并修订编码规则，重抽 30 条再验一次。

## 建议复核者

与两位作者无共事关系的第三方（同学/同行）；记录姓名、日期与是否阅读过正文。

## 输出

- 填好的 `coding-audit-sample30.csv`；
- `audit_coding.py` 输出的一致率/κ 报告；
- 分歧清单（CSV 中 Disagreement 列）。
