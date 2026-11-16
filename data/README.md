# 数据目录

数据**不进 git**，只在这里留一份清单。

## 约定

- 所有数据路径来自环境变量 `CROSSVIEW_DATA_ROOT`，代码里不写死盘符。
- 本目录只放 `README.md` 和 `manifest.json`。
- 大文件、图片、npz、权重一律忽略。

## 设置

```bash
export CROSSVIEW_DATA_ROOT="D:/桌面放置/26年大创"     # Git Bash 当前会话
setx CROSSVIEW_DATA_ROOT "D:\桌面放置\26年大创"       # Windows 永久
```

## 当前数据

格式为 `anyvisloc_ref_png_npy_json_v1`，一个场景约 5.7 GB。

```text
$CROSSVIEW_DATA_ROOT/
└── Scene_01/
    └── Scene_01/
        ├── L01_reference.json     # 参考视图元数据（分辨率、原点、模式）
        ├── aerial_map.png         # 航拍参考图，约 212 MB
        ├── aerial_dsm.npy         # 数字表面模型，约 71 MB
        ├── satellite_map.png      # 卫星参考图（另一种 mode）
        ├── satellite_dsm.npy
        └── L01_0001.npz ... L01_1846.npz
```

目录层级不统一（`Scene_01/Scene_01`），适配器按"含 `*_reference.json`"来定位场景，
所以不需要改代码，也不要求你手动拉平。

### 单个 npz 的字段

| 字段 | 形状 | 含义 |
|---|---|---|
| `image` | (H, W, 3) uint8 | 低空斜视查询图像 |
| `K` | (3, 3) float32 | 相机内参 |
| `dist` | (5,) float32 | 畸变系数 |
| `pose_c2w` / `pose_w2c` | (4, 4) float32 | 相机位姿 |
| `xyz` | (3,) float32 | 世界坐标真值 |
| `euler_deg` | (3,) float32 | 姿态角 |
| `sample_id` / `scene_id` | 标量 | 标识 |

### 参考视图的元数据

`L01_reference.json` 里的 `map_resolution` 与 `map_origin_local` 决定了像素坐标到米制坐标的换算。
**缺了它们，位置只能以像素为单位输出，而且不会报错**——适配器会显式读进契约模型 `SceneReference`。

## 自检

```bash
python scripts/inspect_dataset.py
python scripts/inspect_dataset.py --mode satellite
```

输出场景列表、参考图分辨率、原点与样本数。数字对得上，说明数据挂载正确。

## manifest.json

记录每个数据集的来源与校验值，新人照它核对。字段：

- `name`：数据集名称
- `path`：相对 `CROSSVIEW_DATA_ROOT` 的路径
- `size_bytes`：总大小
- `sha256`：归档文件的校验值（目录型数据集可留空）
- `source`：下载地址或提供方
- `owner`：谁负责放到机器上
