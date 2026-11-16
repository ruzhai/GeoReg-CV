# 参与 CrossView

这份是给人看的。工程细节和 AI 约束在 [AGENTS.md](AGENTS.md)，你不需要背。

## 开始之前

```bash
git clone <repo>
cd crossview
make setup
make check      # 应该全绿
```

`make check` 不绿就先别写代码，找负责人，不要自己想办法绕过。

## 动手前先确认它放在哪

| 你想做的事 | 放这里 |
|---|---|
| 新的匹配器 / 检索器 / 骨干网络 | `adaptors/matchers/`、`adaptors/retrievers/` |
| 新的几何算法（单应、PnP、误匹配剔除） | `core/geometry/` |
| 新的候选选择或回退策略 | `core/routing/` |
| 新的数据集适配 | `adaptors/datasets/` |
| 新的演示脚本 | `pipelines/` |
| 新的画图 | `visualization/` |

不确定就问，不要猜着写。放错地方的代价是别人没法复用你的东西。

## 新增一个方法：照着模板抄

不要从空白文件开始，复制一份已有的改。

1. 复制 `adaptors/matchers/_template.py`，改成你的名字
2. 在 `registry.py` 加一行注册
3. 在 `configs/experiments/` 复制一份 yaml，把 `name` 改成你的
4. 加测试 `tests/adaptors/test_<你的名字>.py`，至少一个成功、一个失败
5. 跑 `make check`
6. 跑一次实验，复制 `experiments/_template/card.yaml` 填好

**判据：如果你的方法必须改代码才能启用，说明接错了地方。**
接对了的话，别人只改 yaml 里的 `name` 就能用你的方法。

## 五个常见错误

```text
❌ 在 core/ 里读图片、import cv2
❌ 用 dict 在函数之间传结果
❌ 把路径写成 D:\桌面放置\...
❌ 测试红了去改断言
❌ 一个 PR 改三个模块
```

## 提交

```text
分支      feat/候选重排
commit    feat: 给候选重排加入内点权重
PR 标题    给候选重排加入内点权重
PR 描述    对应 issue #12
           改了什么：……
           影响契约：无 / 改了 schema（已升 1.1）
           跑过：make check 全绿；Scene_01 前 20 个样本
```

用中文写。三个人都看得快，英文只会让你写得更含糊。

## 每周

- 每个实验写一张实验卡，没跑实验就不用写
- 周会只看实验卡和 issue 板，不看代码
- 卡住了在 issue 里说"试了什么、报错是什么"，不要自己硬试超过两次

## 什么时候可以不走流程

改注释、改文档、改错别字、修 typo，直接提 PR，不用建 issue，不用写实验卡。

**其他一切都走流程。** 流程的作用是让你三个月后还能看懂自己写的东西。
