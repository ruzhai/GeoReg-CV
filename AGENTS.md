# CrossView 工程约定

> 长期稳定的协作与工程约束。不在这里写当前分支、临时进度、某次实验的结论。
> 每次动手前读一遍，然后去看代码和测试，不要凭印象改。
> 人读 [CONTRIBUTING.md](CONTRIBUTING.md)；这份文件是给 AI 助手和代码评审用的。

## 三条硬规则

以下三条不可协商。它们对应三种**一旦发生就无法事后补救**的损害。

### 1. 跨模块传递的数据必须是契约

任何两个模块之间传数据，必须用 `src/crossview/schema/` 里定义的模型。
不允许裸 dict、不允许临时 dataclass、不允许"先传着以后再说"。

传不了 → 先在 `schema/` 加一个类并写测试，再传。

改字段语义或删字段，必须升 `schema_version`，并在 `CHANGELOG.md` 记一笔。

```python
class GeoRegistrationRecord(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    ...
```

### 2. 路径不许写死

禁止出现 `D:\`、`C:/Users/`、`/mnt/` 这类绝对路径。
一切路径从 `schema/configs.py` 读，配置里用环境变量展开；默认值只能相对仓库根。

### 3. 测试不许为了通过而放宽

测试红了只有两种合法处理：

- 代码错了 → 修代码
- 测试过时了 → 修测试，并在 PR 里写清"为什么这个数应该变"

不允许注释掉、跳过用例、放宽断言、删除测试。

## 其余约定

偏离这些不会立刻出事，但要在 PR 里说明理由。

**边界**

- `core/` 不做 IO，不 import cv2 / torch；需要图像就传 numpy 数组进来
- `adaptors/` 不做算法决策，只做外部世界的封装
- `pipelines/` 不做数学计算，只做编排
- 需要 cv2 的处理放到 `adaptors/`，函数返回 numpy

**代码**

- 不新增依赖，除非说明为什么现有依赖不够
- 不用 `print`，用 `logging`
- 不吞异常；失败要有结构化原因，写进 `failed_reason`
- 函数超过 80 行、文件超过 500 行，先判断是否该拆
- 随机性必须可复现：固定 seed，并写进实验卡

**协作**

- 和人交流、写 commit / PR / issue 用中文；代码和标识符用英文
- 先分清当前是讨论诊断还是实现；讨论阶段不改代码，除非明确要求
- 一次只推进一个可检查的步骤，做完说清楚再停
- 动手前说明预期行为和改动范围；涉及接口、状态机、跨模块数据流的变化，先讲清再改
- 不确定就问，不要猜着写
- 不顺手重构、不提前抽象、不为"以后可能用到"做设计

**Git**

- 不主动 commit / push / 切分支 / 改历史，除非明确要求
- 分支：`feat/短描述`、`fix/短描述`、`exp/短描述`
- commit：`type: 中文描述`，type ∈ `feat` / `fix` / `exp` / `docs` / `test` / `refactor` / `chore` / `ci`
- 一次 commit 只做一件事；测试和它验证的行为放在同一个 commit

**评审**

- 一个 PR 只做一件事；如果你说不清它做了什么，就该拆
- 评审一次只提一个问题，先说最重要的
- 不修改别人的分支，不替作者改代码，除非被要求
- 评审问题，不是评审风格偏好

## 项目结构

所有代码在 `src/crossview/` 下。

| 目录 | 负责 | 不负责 |
|---|---|---|
| `schema/` | 数据形状、枚举、Protocol、序列化 | 任何业务逻辑 |
| `core/timealign/`（规划） | 时延建模、补帧、时间对齐 | 网络仿真器本身 |
| `core/geometry/` | 单应、PnP、重投影、拓扑约束 | 文件与图像 IO |
| `core/routing/` | 候选选择与回退决策 | 匹配计算 |
| `core/metrics/` | 精度与成功率统计 | 数据加载 |
| `imaging/` | 需要图像库的算法（允许 cv2） | 文件读写 |
| `adaptors/datasets/` | 数据集适配 | 算法决策 |
| `adaptors/matchers/` | 匹配器实现（含 `_template.py`） | 路由决策 |
| `adaptors/retrievers/` | 检索器实现 | 路由决策 |
| `adaptors/backbones/` | 轻量骨干网络 | 路由决策 |
| `adaptors/io/` | 结果读写、产物落盘、仿真导出 | 数学计算 |
| `pipelines/` | 编排 | 数学计算 |
| `visualization/` | 画图 | 任何计算 |
| `cli/` | 命令行入口，每个 ≤50 行 | 业务逻辑 |

`tools/` 放一次性脚本与分析工具，`matlab/` 放 MATLAB 仿真，都不属于运行时包。

## 分工

| 范围 | 负责人 |
|---|---|
| `core/timealign/`、`adaptors/datasets/` | fcc |
| `core/geometry/`、`core/routing/`、`core/metrics/` | 用户 |
| `adaptors/matchers/`、`adaptors/backbones/` | 用户 |
| `schema/` | 改动必须对方 review |
| `configs/`、`docs/`、`tests/fixtures/`、`pipelines/` | 用户 |

两个人在同一个分支上并行改不同目录；改对方的目录走 PR。改 `schema/` 必须先合对方确认——只有两个人时，这是唯一能防止契约被单方面改掉的机制。

## 文档与实验

- 设计文档进 `docs/design-docs/`，按阶段命名
- 每个不可逆的技术决定写一页 ADR，进 `docs/adr/`
- 每个实验一份 `card.yaml` 进 `experiments/<id>/`；只提交 card 和 summary，不提交产物
- 周会材料进 `docs/weekly-material/`
- 文档里的路径和命令必须能在当前仓库跑通，不许写"理论上的"路径
