# 权重目录

模型权重**不进 git**。

## 约定

- 路径来自环境变量（默认 `${CROSSVIEW_DATA_ROOT}/weights`）。
- 只读：跑实验不要往这里写新权重，输出到 `experiments/<id>/`。
- 记录每个权重的来源、训练配置和 sha256，写在 `manifest.json`。

## 常见权重

| 权重 | 用途 | 来源 |
|---|---|---|
| CAMP 检索 | 参考视图检索 | 待填 |
| RoMa | 跨视角稠密匹配 | 待填 |
| MobileNetV3 | 轻量化检索骨干 | torchvision 预训练 |
