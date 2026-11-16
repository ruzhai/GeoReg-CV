# 测试夹具

## golden/

放"冻结样本"：一组确定的输入 + 一次被认可的期望输出。

```text
tests/fixtures/golden/
├── case_01/
│   ├── observer.npz          # 或 png
│   ├── reference_tile.png
│   └── expected.json         # {"pred": [x, y, z], "error_m": 0.446, "route": "top1_fast_path"}
└── case_02/
```

### 怎么冻结

1. 挑 5 个样本：3 个成功、1 个边界、1 个失败。
2. 用当前代码跑一次，把结果写进 `expected.json`。
3. **人工确认这些结果是对的**——golden 会固化现状，包括 bug。
4. 从此每次改代码都要和它比对。

### 什么时候可以改 expected.json

只有当改动是**有意的**，并且 PR 里写清了"为什么这个数应该变"。

为了让测试通过而改 golden，和改断言放宽是同一种错误。

### 注意

- 夹具要小（每个 case < 500KB），因为要进 git。
- 不要放真实数据集的大图，裁剪出局部即可。
