# 方法设计草案

## Baseline

AnyVisLoc 官方流程：

```text
Query image
  -> CAMP retrieval
  -> RoMa matching
  -> P3P localization
  -> estimated position
```

## 拟改进方向

优先选择：几何先验引导的 Top-K 候选重排序与几何一致性验证。

动机来自 Scene_01 初步分析：检索不是主要耗时瓶颈，严重误差样本常与候选选择、匹配内点数和几何一致性有关。因此，先不大改 backbone，而是在 AnyVisLoc baseline 的候选决策阶段加入更稳的几何评分。

初步评分形式：

```text
final_score = retrieval_score
            + alpha * normalized_inliers
            - beta  * reprojection_error
            + gamma * pose_prior_consistency
```

后续消融：

- Baseline AnyVisLoc
- + inlier reranking
- + reprojection-error filtering
- + yaw/pitch prior
- + DSM/geometric consistency

## CDA-FastReg

当前工程采用 `CDA-FastReg` 作为快速配准系统方法名称，即置信度驱动的自适应快速空间配准方法。该方法不重新训练模型，而是在 AnyVisLoc baseline 的 Top1 / TopK 路径之间加入置信度决策层：

```text
Top1 fast path
    ↓
best_inliers >= threshold ?
    ├── Yes: output Top1 geo-position
    └── No : fallback to Top2/Top5 robust registration
```

当前推荐配置：

```text
threshold = 1000
fallback = Top2
```

