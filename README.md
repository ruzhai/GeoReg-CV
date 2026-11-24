# CrossView

跨视角协同感知：把空中平台与地面终端在不同时刻、不同视角拍到的图像，对齐到同一时空坐标，
输出可比较的目标位置。

技术路线分三条线，共享一套数据契约：

| 线 | 解决的问题 | 目录 |
|---|---|---|
| 时间对齐 | 异步链路导致多源数据时序错位、丢帧 | `src/crossview/core/timealign/` |
| 空间配准 | 60°–90° 视角差与跨模态辐射差异导致匹配失效 | `src/crossview/core/geometry/`、`core/routing/` |
| 轻量化重识别 | 边缘算力受限下的跨视角目标关联 | `src/crossview/adaptors/backbones/` |

## 当前状态

| 能力 | 状态 |
|---|---|
| 契约层（schema / 配置 / 序列化） | 可用，有测试 |
| CDA-FastReg 置信度驱动路由 | 可用，有测试 |
| 在线单样本配准（检索 → 匹配 → 定位） | 代码已迁入，需数据集运行 |
| 批量跑分与结果汇总 | 同上 |
| 可视化与仿真数据导出 | 同上 |
| 时间对齐（研究内容一） | 未开始 |
| 轻量化跨视角重识别（研究内容三） | 未开始 |
| golden 夹具 | 待冻结，见 `tests/fixtures/README.md` |
| CI（lint + 类型 + 契约测试） | 已配置 |

## 快速开始

```bash
git clone git@github.com:ruzhai/GeoReg-CV.git
cd GeoReg-CV

python -m venv .venv --system-site-packages
source .venv/Scripts/activate        # Git Bash；PowerShell 用 .venv\Scripts\Activate.ps1
pip install -e ".[dev]"

crossview-info                       # 自检：版本、包路径、已注册组件
python scripts/check.py              # lint + 类型 + 测试
```

`scripts/check.py` 不绿就不要开始写代码。见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 目录

```text
src/crossview/
├── schema/       契约：records / samples / configs / enums / interfaces / serialization
├── core/         纯计算，不读文件、不依赖框架
│   ├── geometry/   单应、PnP、拓扑约束
│   ├── routing/    置信度路由与结果构建
│   ├── metrics/    指标统计
│   └── timealign/  时间对齐（规划）
├── imaging/      需要图像库的算法（允许 cv2，但不做文件 IO）
├── adaptors/     外部世界的封装
│   ├── datasets/   数据集适配
│   ├── matchers/   匹配器（含新方法模板）
│   ├── retrievers/ 检索器
│   ├── backbones/  轻量骨干
│   └── io/         结果读写、产物落盘、仿真导出
├── pipelines/    编排层
├── visualization/画图
└── cli/          命令行入口
```

脚本类工具放 `tools/`，MATLAB 仿真放 `matlab/`。

## 跑一次配准

需要数据集和权重，见 [data/README.md](data/README.md)。

```bash
export CROSSVIEW_DATA_ROOT="D:/桌面放置/26年大创"
python scripts/inspect_dataset.py      # 先确认数据挂对了

python -m crossview.pipelines.run_online_cda_sample --help
python -m crossview.pipelines.run_online_cda_sample \
    --scene Scene_01 --sample-id L01_0001 \
    --config configs/anyvisloc_baseline.yaml
```

批量：

```bash
python -m crossview.pipelines.run_online_cda_batch --scene Scene_01 --limit 20
```

单次运行会在 `outputs/online_cda/<scene>/<sample>/<时间戳>/` 下产出一份完整记录，
`outputs/` 不进 git。

## 协作

- 工程约定：[AGENTS.md](AGENTS.md)（规则本体）、[CONTRIBUTING.md](CONTRIBUTING.md)（新人全流程：环境、分支、提交、测试、PR）
- **全部文档索引：[docs/README.md](docs/README.md)**
- 契约说明：`docs/contracts/`
- 设计文档：`docs/design-docs/`
- 实验卡：`experiments/_template/card.yaml`

三条硬规则：**跨模块传数据必须用契约**、**路径不许写死**、**测试不许为了通过而放宽**。
