# 用 Agent 上手 CrossView

> 这份文档不是部署教程，也不是 Python 教学。
> 它讲的是：**怎么让 AI Agent 读懂这个仓库、遵守它的规范、并且产出你能验收的改动。**

## 0. 前提：仓库在这台机器上

只有这一步需要你动手，后面基本都可以交给 Agent。

```bash
git clone git@github.com:ruzhai/GeoReg-CV.git
cd GeoReg-CV
python -m venv .venv --system-site-packages
source .venv/Scripts/activate        # Git Bash
pip install -e ".[dev]"
```

## 1. 第一件事：让它先读规范，别急着改代码

在仓库根目录打开 Agent，把这段贴进去：

```text
先读 AGENTS.md、docs/README.md、src/crossview/schema/__init__.py，
然后回答三个问题：
1. 这个项目的三条硬规则是什么？
2. 我要新增一个匹配器，需要动哪些文件？
3. 哪些目录我不该碰？
先不要改任何文件。
```

这一步的目的不是学知识，是**确认它真的读了**。它答得含糊或者编造路径，后面的活别交给它。

## 2. 让它建立项目地图

```text
给我一张表：src/crossview/ 下每个子目录负责什么、不负责什么；
再指出四条线（时间对齐 / 空间配准 / 重识别 / 系统集成）各自的代码入口。
```

期望产出是一张能直接贴进 PR 描述的表。如果它写出了仓库里不存在的目录，说明它在猜。

## 3. 提需求的方式

四行模板，缺一行它就会自由发挥：

```text
背景：为什么要做这个改动
要改哪里：具体到文件或目录
期望行为：改完之后什么变了
不能动：契约 src/crossview/schema/、测试断言
验收：python scripts/check.py 全绿
```

## 4. 第一个任务：加一个空壳，不写实现

不要一上来就让它实现算法。先让它走通接入流程：

```text
照 src/crossview/adaptors/matchers/_template.py 复制一份，
类名改成 XxxMatcher，注册名 xxx，
match() 里先 raise NotImplementedError，旁边写一行 TODO 说明要怎么实现。
然后在 configs/ 下加一份 yaml，让配置里能选中它。
最后加一个测试，只验证注册成功。
```

**判据：不改代码、只改 yaml 里的 name，就能选中你的方法。**做不到说明接错了地方。

## 5. 验收 Agent 的产出

三件事，顺序不能反：

1. **跑 `python scripts/check.py`** —— 不绿不合
2. **看 diff** —— 改了多少行？有没有动不相干的文件？
3. **问它"为什么这么改"** —— 答不上来的地方，就是你不该合的地方

**理解门槛**：核心算法代码，你必须能讲清每一步在干什么。讲不清就先别合，让它重写，或者你自己拆小。

## 6. 红线：Agent 最常犯的四种错

| 错误做法 | 为什么危险 | 怎么拦 |
|---|---|---|
| 改 schema 但不升版本 | 旧的落盘结果读不出来 | 契约改动必须人工确认 |
| 为了让测试过而放宽断言 | 永久失去发现问题的能力 | 只允许「修代码」或「改测试+说明理由」 |
| 写死 `D:\...` 路径 | 换机器直接崩 | CI + review |
| 一次改很多文件 | 出问题无法定位 | 一个 PR 只做一件事 |

## 7. 这些事不要交给 Agent

- **决定做什么**：范围、优先级、先做哪条线
- **判断结果对不对**：精度够不够、失败原因是什么
- **合并前的最终 review**
- **契约变更**：改 `src/crossview/schema/` 必须人看

## 附录：常用命令

```bash
crossview-info                    # 自检：版本、路径、已注册组件
python scripts/check.py           # lint + 格式 + 类型 + 测试
python scripts/export_schemas.py  # 改了契约后重新导出 JSON Schema
```

详细的工程规则见 [AGENTS.md](AGENTS.md)，文档分类见 [docs/README.md](docs/README.md)。
