# GeoReg-CV

面向观察者视角与无人机/航拍参考视角协同感知的跨平台空间配准工程。

本工程当前阶段以 AnyVisLoc 作为 baseline 与数据来源，但研究对象不等同于 AnyVisLoc 官方工程本身。这里的目标是把任务明确抽象为：

```text
Observer-view image
    ↓
Reference-view retrieval
    ↓
Cross-view feature matching
    ↓
Geometry-guided registration
    ↓
Geo-position estimation
```

## 当前工程定位

- `observer_view`：观察者/低空斜视图像，可由 AnyVisLoc 的低空 UAV oblique query 图像近似。
- `reference_view`：无人机/航拍/正射参考视图，可由 AnyVisLoc 的 aerial map / orthophoto reference 表示。
- `geo_position`：最终输出的空间位置或相机位姿。
- `AnyVisLoc baseline`：作为第一组几何配准 baseline，用于复现、分析与后续改进。

## 推荐数据与官方工程路径

默认假设本机已有：

```text
D:/GD/Benchmark
D:/GD/Benchmark/Data/AnyVisLoc
D:/GD/Benchmark/weights
```

本工程不会复制大体量数据和权重，只在配置中引用它们。

## 第一阶段目标

1. 用本工程入口调用 AnyVisLoc baseline；
2. 固化 Scene_01 / limit=20 的 baseline 结果；
3. 分析成功/失败样本、耗时瓶颈；
4. 在 baseline 上加入几何先验引导的候选重排序与一致性验证。

## 当前系统级命令

基于已固化的 Scene_01 full baseline 结果，生成课题系统需要的位置输出、可视化与仿真数据：

```powershell
cd /d D:\GeoReg-CV
python .\pipelines\run_system_demo.py
```

输出目录：

```text
D:/GeoReg-CV/outputs/scene01_system_demo
```

该命令不会重新跑模型，只会把 baseline 的结果转化为完整系统交付物。

生成成功/失败样本可视化图：

```powershell
cd /d D:\GeoReg-CV
python .\pipelines\generate_sample_visualizations.py
```

输出目录：

```text
D:/GeoReg-CV/outputs/scene01_sample_visualizations
```

导出 CDA-FastReg 方法报告、实验表和流程图：

```powershell
cd /d D:\GeoReg-CV
python .\tools\simulate_adaptive_strategy.py
python .\tools\export_adaptive_method_artifacts.py
```

关键输出：

```text
D:/GeoReg-CV/experiments/fast_baseline_ablation/adaptive_method_artifacts
D:/GeoReg-CV/docs/cda_fastreg_method_report.md
D:/GeoReg-CV/docs/figures/cda_fastreg_flow.svg
```

生成带自适应路径信息的系统演示与可视化：

```powershell
cd /d D:\GeoReg-CV
python .\pipelines\run_adaptive_system_demo.py
python .\pipelines\generate_adaptive_visualizations.py
```

关键输出：

```text
D:/GeoReg-CV/outputs/scene01_cda_fastreg_demo
D:/GeoReg-CV/outputs/scene01_cda_fastreg_visualizations
```
