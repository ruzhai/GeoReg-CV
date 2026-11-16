# CDA-FastReg 自适应快速空间配准方法

## 方法名称

- 中文：置信度驱动的自适应快速空间配准方法
- 英文：Confidence-Driven Adaptive Fast Registration
- 简写：CDA-FastReg

## 方法动机

AnyVisLoc 标准 Top5 流程定位较稳健，但单样本平均耗时较长。固定 Top1 快速路径可以降低耗时，但严重失败样本明显增加。因此，本文采用自适应策略：优先使用 Top1 快速路径，并利用匹配内点数评估定位置信度；当置信度不足时，自动回退到 Top2 或 Top5 精配准路径。

## 在线策略

```text
1. 输入观察者视角图像；
2. 执行 Top1 快速配准；
3. 读取 Top1 的 best_inliers；
4. 若 best_inliers >= T，则接受 Top1 输出；
5. 否则回退到 Top2 / Top5 精配准；
6. 输出最终空间位置。
```

当前推荐配置：

```text
T = 1000
fallback = Top2
```

## 实验结果表

| Method | Success@1m(%) | Success@3m(%) | Success@5m(%) | Mean Error(m) | Median Error(m) | Mean Time(s) | Speedup | Fallback Ratio(%) | >20m |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard_Top5 | 87.50 | 97.50 | 98.33 | 4.39 | 0.435 | 23.72 | 1.00x | 0.00 | 1 |
| Fixed_Top2 | 82.50 | 99.17 | 99.17 | 4.87 | 0.467 | 22.32 | 1.06x | 0.00 | 1 |
| Fixed_Top1 | 78.33 | 90.00 | 91.67 | 90.69 | 0.529 | 16.42 | 1.45x | 0.00 | 10 |
| Adaptive_T1000_else_Top2 | 83.33 | 97.50 | 99.17 | 4.93 | 0.511 | 17.43 | 1.36x | 8.33 | 1 |
| Adaptive_T1500_else_Top2 | 83.33 | 97.50 | 99.17 | 4.93 | 0.511 | 17.43 | 1.36x | 8.33 | 1 |
| Adaptive_T1000_else_Top5 | 83.33 | 96.67 | 98.33 | 4.48 | 0.491 | 17.23 | 1.38x | 8.33 | 1 |

## 推荐方法结果

`Adaptive_T1000_else_Top2`：

- Success@5m：99.17%
- Mean Error：4.93 m
- Median Error：0.511 m
- Mean Time：17.43 s
- Speedup：1.36×
- Fallback Ratio：8.33%

## 论文表述建议

针对固定 Top1 策略速度快但鲁棒性不足、固定 TopK 策略鲁棒但耗时较高的问题，本文设计了一种置信度驱动的自适应快速空间配准方法 CDA-FastReg。该方法首先执行 Top1 快速配准，并根据匹配内点数判断定位结果可靠性；当内点数低于阈值时，系统自动回退至 Top2 精配准路径。实验表明，该策略在保持较高定位成功率的同时显著降低平均运行时间。

## 相关文件

- 实验表：`D:\GeoReg-CV\experiments\fast_baseline_ablation\adaptive_method_artifacts\table_cda_fastreg_ablation.csv`
- 方法流程图：`D:\GeoReg-CV\docs\figures\cda_fastreg_flow.svg`
- 原始模拟结果：`D:\GeoReg-CV\experiments\fast_baseline_ablation\adaptive_strategy_simulation\adaptive_strategy_summary.csv`
