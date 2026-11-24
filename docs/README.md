# 文档索引

> 每个文件一句话说明"它是什么、什么时候该读"。
> **新增文档时请同时在下面加一行**，否则下一个人又不知道它是干什么的。

## 目录怎么分

| 目录 | 放什么 | 生命周期 |
|---|---|---|
| `proposals/` | 方案、汇报稿、团队讨论材料 | 讨论中，未实施 |
| `design-docs/` | 事前做的技术决定 | 改动少，改时说明理由 |
| `guides/` | 具体怎么操作 | 随代码更新 |
| `reports/` | 跑完之后的结论 | 一般不再改，新结论新开一篇 |
| `contracts/` | 接口与数据格式的约定 | 严格，改动要升版本 |
| `adr/` | 不可逆决策的记录 | 只增不改 |
| `schema/` | 脚本导出的 JSON Schema | **自动生成，不要手改** |
| `figures/` | 文档引用的图 | 随文档更新 |

判断新文档放哪：**它是在说"打算做什么"（proposals）、"为什么这么设计"（design-docs）、"怎么做"（guides），还是"做完了结果如何"（reports）。**

## 写作约定

- **未完成的工作一律标 TODO**：清单项用 `- [ ]`，标题上用小标题后缀 `【TODO】`
- 文档开头写清来源和状态（讨论稿 / 已实施 / 已废弃）
- 不写"以后再补"的占位段落，要么写 TODO，要么删掉

## proposals/ — 方案与汇报

- [overall-proposal.md](proposals/overall-proposal.md) — 整体实现与调研方案（讨论稿）：系统目标、两条数据流、公开数据集选型、实验设计、下一步调研分工。**尚未实施**，待办见文末。
- [project-arrangement.md](proposals/project-arrangement.md) — 六阶段计划与 A/B/C/D 四角色分工。**六个阶段均未开始**。
- `source/` — 上述两份材料的原始 PDF / DOCX。

## design-docs/ — 设计

- [system_design.md](design-docs/system_design.md) — 课题系统的整体分层、模块职责与系统级输出。
- [method_design.md](design-docs/method_design.md) — 方法草案：CDA-FastReg 的动机、评分形式与消融计划。
- [engineering_notes.md](design-docs/engineering_notes.md) — 为什么不直接改 AnyVisLoc；论文概念与工程命名的映射。

## guides/ — 操作指南

- [online_cda_single_sample.md](guides/online_cda_single_sample.md) — 单样本在线定位的命令、参数、输出文件与已验证性能。

## reports/ — 实验报告

- [scene01_baseline_analysis_report.md](reports/scene01_baseline_analysis_report.md) — Scene_01 全量 baseline（2026-08-09）：精度、误差分布、耗时瓶颈与高误差样本。
- [cda_fastreg_method_report.md](reports/cda_fastreg_method_report.md) — CDA-FastReg 与固定 Top1/Top2/Top5 的对照结果与推荐配置。

## contracts/ — 契约

- [README.md](contracts/README.md) — 五类契约的说明、修改规则，以及为什么不能直接用 dict。

## schema/ — 自动生成

由 `python scripts/export_schemas.py` 生成，供 MATLAB 等非 Python 消费方校验字段。
**不要手改**，改了会在下次导出时被覆盖。
