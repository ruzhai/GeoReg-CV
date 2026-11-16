# 第三方工程

这里用 git submodule 固定外部工程，**不复制代码进来**。

## 为什么用 submodule

- 版本可追溯：论文和报告里要写清复现的是哪个 commit。
- 不污染 lint / 覆盖率统计。
- 不把别人的几万行代码塞进自己的历史。

## 目录

| 目录 | 对应工程 | 固定版本 |
|---|---|---|
| `AnyVisLoc/` | 官方 baseline 与数据接口 | 待填 commit |

## 添加一个 submodule

```bash
git submodule add <url> third_party/AnyVisLoc
git commit -m "chore: 以 submodule 固定 AnyVisLoc baseline"
```

别人 clone 之后需要：

```bash
git submodule update --init --recursive
```
