# GeoReg-CV 工程说明

## 为什么不直接改 AnyVisLoc

AnyVisLoc 是本课题当前最合适的 baseline 和数据来源，但论文工程不应该完全等同于官方工程。我们保留官方工程用于复现，把自己的工程作为任务抽象、实验管理和后续方法改进的主入口。

## 任务映射

| 论文任务概念 | 工程命名 | AnyVisLoc 中的对应 |
| --- | --- | --- |
| 观察者视角 | observer_view | 低空斜视 query 图像 |
| 无人机/航拍参考视角 | reference_view | aerial map / orthophoto |
| 跨平台空间配准 | spatial_registration | retrieval + matching + PnP |
| 地理位置输出 | geo_position | query pose / local coordinate |

## 第一阶段实验

1. 用 `pipelines/run_anyvisloc_baseline.py` 调用官方 AnyVisLoc；
2. 先跑 `limit=20` 快速验证；
3. 再跑 Scene_01 或全数据；
4. 固化结果；
5. 从失败样本中设计几何引导改进。

