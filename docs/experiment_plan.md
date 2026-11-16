# 实验计划

## 阶段 1：baseline 固化

- 数据集：AnyVisLoc
- 场景：先 `limit=20`，再 `Scene_01`
- 方法：CAMP + RoMa + P3P
- 指标：
  - mean localization error
  - median localization error
  - success@1m / 3m / 5m / 10m / 20m
  - Recall@K
  - PDM@K
  - retrieval time
  - matching time
  - PnP time
  - total time

## 阶段 2：失败样本分析

重点看：

- 高误差样本；
- 检索 rank 较低的样本；
- 匹配内点数过少的样本；
- 候选中存在更优定位但最终未选中的样本；
- 耗时异常样本。

## 阶段 3：几何引导改进

先实现候选重排序，不急着训练新模型。

