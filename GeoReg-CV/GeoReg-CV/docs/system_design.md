# GeoReg-CV 课题系统设计

## 系统目标

GeoReg-CV 的目标不是只复现某个 benchmark 指标，而是形成一个完整的跨平台空间配准系统：

```text
观察者视角图像
  -> 无人机/航拍参考视图
  -> 跨视角空间配准
  -> 地理位置估计
  -> 结果分析与仿真展示
```

## 当前实现

当前版本使用 AnyVisLoc baseline 作为核心算法实现：

- 检索：CAMP
- 匹配：RoMa
- 几何定位：P3P / PnP
- 数据：AnyVisLoc Scene_01

GeoReg-CV 在此基础上补齐课题系统所需的工程层：

| 模块 | 作用 |
| --- | --- |
| `datasets` | 将 AnyVisLoc 数据映射为观察者视角与参考视角 |
| `views` | 定义 observer view 和 reference view |
| `registration` | 定义检索、匹配、几何定位接口 |
| `system` | 统一结果结构、结果读取、样本选择、仿真数据导出 |
| `visualization` | 生成真实位置与估计位置对比图 |
| `pipelines` | 提供 baseline 运行入口和系统演示入口 |
| `outputs` | 保存系统级位置输出、展示图和仿真数据 |

## 系统级输出

运行 `pipelines/run_system_demo.py` 后会生成：

- 全部样本位置估计结果；
- 成功/边界/失败样本展示集；
- 仿真软件可读取的 JSON 点位数据；
- 真实位置与估计位置 SVG 对比图；
- 系统演示摘要。

