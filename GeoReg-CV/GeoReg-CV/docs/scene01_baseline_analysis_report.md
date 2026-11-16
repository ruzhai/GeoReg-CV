# Scene_01 AnyVisLoc Baseline 结果分析报告

## 1. 实验设置

- 工程：GeoReg-CV
- 数据集：AnyVisLoc
- 场景：Scene_01
- Baseline：CAMP + RoMa + P3P
- 参考视角：aerial
- 位姿先验：yaw / pitch，配置中记为 `yp`
- 样本数：1846
- 结果来源：`D:\GeoReg-CV\experiments\baseline_anyvisloc_scene01\20260809-2323_1scenes\aerial\aerial-CAMP-Roma-yp`
- 固化目录：`D:\GeoReg-CV\experiments\baseline_anyvisloc_scene01\frozen_scene01_full_baseline_20260809-2323`

## 2. 完整性检查

| 项目 | 数值 |
| --- | ---: |
| 请求样本数 | 1846 |
| 实际结果数 | 1846 |
| PnP 成功数 | 1846 |
| PnP 失败数 | 0 |
| 异常失败数 | 0 |
| failure rate | 0.0000 |

结论：本次 Scene_01 full baseline 已完整运行，未出现异常失败或 PnP 失败。

## 3. 定位精度

| 指标 | 数值 |
| --- | ---: |
| Mean Error | 7.8665 m |
| Median Error | 0.4773 m |
| Max Error | 4298.6377 m |
| Success@1m | 87.27% |
| Success@3m | 99.02% |
| Success@5m | 99.51% |
| Success@10m | 99.62% |
| Success@20m | 99.62% |
| Recall@5 | 95.07% |
| PDM@5 | 0.6735 |

核心观察：中位误差只有 0.4773 m，说明大多数样本定位较准；但平均误差达到 7.8665 m，主要被少数极端大误差样本拉高。

## 4. 误差分布

| 误差区间 | 样本数 | 占比 |
| --- | ---: | ---: |
| <=1m | 1611 | 87.27% |
| 1-3m | 217 | 11.76% |
| 3-5m | 9 | 0.49% |
| 5-10m | 2 | 0.11% |
| 10-20m | 0 | 0.00% |
| >20m | 7 | 0.38% |

其中误差大于 5m 的样本有 9 个，误差大于 20m 的严重失败样本有 7 个。

## 5. 高误差样本 Top 10

| 样本 | 误差/m | GT Rank | Recall@5 | Best Inliers |
| --- | ---: | ---: | ---: | ---: |
| L01_0816 | 4298.64 | 23 | 0 | 476 |
| L01_1705 | 3485.20 | 17 | 0 | 269 |
| L01_0572 | 2936.52 | 7 | 0 | 224 |
| L01_1513 | 1442.71 | 16 | 0 | 414 |
| L01_0054 | 805.42 | 10 | 0 | 269 |
| L01_1450 | 364.59 | 7 | 0 | 343 |
| L01_1498 | 99.28 | 2 | 1 | 2999 |
| L01_1224 | 6.25 | 1 | 1 | 2994 |
| L01_0047 | 5.49 | 3 | 1 | 2929 |
| L01_1598 | 4.29 | 1 | 1 | 2993 |

从高误差样本看，部分严重失败样本的 `Recall@5=0`，说明真实候选没有进入 Top-5，属于检索阶段失败；也存在少量 `Recall@5=1` 但误差仍较大的样本，说明检索命中后仍可能出现候选选择或几何定位不稳定。

## 6. 耗时分析

| 指标 | 数值 |
| --- | ---: |
| 平均总耗时/样本 | 21.1196 s |
| 中位总耗时/样本 | 18.8080 s |
| 平均检索耗时/样本 | 0.019713 s |
| 中位检索耗时/样本 | 0.016217 s |

检索耗时远小于单样本总耗时，说明当前系统主要耗时不在图像检索，而在后续候选区域处理、跨视角匹配和几何定位流程。

## 7. 对课题的意义

本次实验已经证明，GeoReg-CV 可以基于 AnyVisLoc baseline 完成从观察者/斜视图像到无人机/航拍参考视图的空间配准，并输出位置估计结果。该结果可以作为课题的第一组正式 baseline。

后续如果暂不做算法改进，也可以继续围绕完整系统展开：

1. 输出定位结果可视化；
2. 生成成功/失败样本对比图；
3. 整理模块耗时与误差统计；
4. 接入仿真软件进行位置点、误差连线和轨迹展示。

## 8. 已生成文件

- `scene01_metrics_summary.csv`
- `scene01_metrics_summary.json`
- `scene01_error_buckets.csv`
- `scene01_enriched_results.csv`
- `scene01_top30_high_error_samples.csv`
- `scene01_top30_slow_samples.csv`
- `scene01_baseline_analysis_report.md`
