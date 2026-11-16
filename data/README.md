# 数据目录

数据**不进 git**，只在这里留一份清单。

## 约定

- 所有数据路径来自环境变量 `CROSSVIEW_DATA_ROOT`，代码里不写死盘符。
- 本目录只放 `README.md` 和 `manifest.json`。
- 大文件、图片、npz、权重一律忽略。

## 设置

```bash
export CROSSVIEW_DATA_ROOT="D:/GD/Benchmark"     # Git Bash
setx CROSSVIEW_DATA_ROOT "D:\GD\Benchmark"       # Windows 永久
```

## 期望的目录结构（AnyVisLoc）

```text
$CROSSVIEW_DATA_ROOT/
└── Data/AnyVisLoc/
    ├── Scene_01/
    │   ├── aerial_map.png
    │   ├── aerial_dsm.npy
    │   └── *.npz
    └── Scene_02/
```

## manifest.json

记录每个数据集/权重的来源与校验值，新人照它核对，缺什么一目了然。
字段说明见文件内注释（JSON 不支持注释，写在这里）：

- `name`：数据集名称
- `path`：相对 `CROSSVIEW_DATA_ROOT` 的路径
- `size_bytes`：总大小
- `sha256`：归档文件的校验值（目录型数据集可留空）
- `source`：下载地址或提供方
- `owner`：谁负责放到机器上
