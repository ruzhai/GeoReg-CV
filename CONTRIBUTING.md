# 贡献指南

从"还没装 Git"到"你的改动被合并"，按顺序走一遍就通了。
日常写代码主要靠 Agent，所以文中会给可直接粘贴的 prompt；但 Git 和测试这几步必须你自己清楚。

---

## 0. 一次性准备

### 0.1 拿到仓库权限

找仓库 owner 把你的 GitHub 账号加为协作者（write 权限）。收到邮件邀请后点接受。

确认能访问：打开 <https://github.com/ruzhai/GeoReg-CV>，能看到代码就对了。

### 0.2 装 Git 并配置身份

```bash
git --version                                  # 没有就去 git-scm.com 装
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"      # 建议与 GitHub 账号一致
```

### 0.3 配置认证（二选一）

**推荐 SSH：**

```bash
ssh-keygen -t ed25519 -C "你的邮箱"      # 一路回车即可
cat ~/.ssh/id_ed25519.pub                # 复制输出的整行
```

把复制的内容贴到 GitHub → Settings → SSH and GPG keys → New SSH key。

验证：

```bash
ssh -T git@github.com
# 看到 "Hi 你的用户名! You've successfully authenticated" 就成功
```

**或者用 HTTPS + Token：** 在 GitHub → Settings → Developer settings → Personal access tokens 生成一个带 `repo` 权限的 token，clone 时当密码用。

### 0.4 克隆并跑起来

```bash
git clone git@github.com:ruzhai/GeoReg-CV.git
cd GeoReg-CV

python -m venv .venv --system-site-packages
source .venv/Scripts/activate          # Git Bash；PowerShell 用 .venv\Scripts\Activate.ps1
pip install -e ".[dev]"

crossview-info                         # 自检：版本、路径、已注册组件
python scripts/check.py                # 应该全绿
```

`check.py` 不绿先别写代码，见第 6 节。

---

## 1. 每天的工作循环

七步，按顺序做。

### 第 1 步：同步主分支

```bash
git switch main
git pull --ff-only
```

先拉最新，避免在旧代码上开发。

### 第 2 步：开一个分支

```bash
git switch -c feat/候选重排
```

命名规则：

| 前缀 | 用于 |
|---|---|
| `feat/` | 新功能、新方法 |
| `fix/` | 修 bug |
| `exp/` | 实验性改动，可能不合并 |
| `docs/` | 只改文档 |

分支名用中文没问题，但不要有空格。

### 第 3 步：让 Agent 干活

先把这段贴给 Agent，确认它读过规范：

```text
先读 AGENTS.md 和 CONTRIBUTING.md，然后回答：
1. 三条硬规则是什么？
2. 我要做的这件事应该改哪个目录？
先不要动文件。
```

再按四行模板提需求：

```text
背景：为什么要做这个改动
要改哪里：具体到文件或目录
期望行为：改完之后什么变了
不能动：契约 src/crossview/schema/、测试断言
验收：python scripts/check.py 全绿
```

### 第 4 步：本地验证

```bash
python scripts/check.py        # lint + 格式 + 类型 + 测试，一次跑完
```

只想快速跑测试：

```bash
python -m pytest tests -q
```

### 第 5 步：提交

```bash
git add <你改的文件>           # 不要用 git add -A，避免把临时文件带进去
git commit -m "feat: 给候选重排加入内点权重"
```

提交信息格式：`type: 中文描述`。type 只能是：

```text
feat      新功能
fix       修 bug
exp       实验性改动
docs      文档
test      测试
refactor  重构（不改行为）
chore     杂项（依赖、配置）
ci        CI 配置
```

一个 commit 只做一件事。测试和它验证的行为放在同一个 commit。

### 第 6 步：推送

```bash
git push -u origin feat/候选重排
```

### 第 7 步：开 PR

```bash
gh pr create --fill        # 或者直接去 GitHub 网页点 "Compare & pull request"
```

PR 描述按模板填四栏：对应 issue、改了什么、影响了哪个契约、跑了哪些检查。

提交后 CI 会自动跑，绿色才能合并。改到别人负责的目录，`CODEOWNERS` 会自动请求对方 review。

---

## 2. 测试怎么写

### 什么时候必须写

| 改了什么 | 要不要测试 |
|---|---|
| `src/crossview/core/` | **必须**，而且要对得上真实性（见下） |
| `src/crossview/adaptors/` | 必须，至少一个契约测试 |
| `src/crossview/schema/` | 必须，改契约必须配测试 |
| `pipelines/`、文档、配置 | 不强制 |

### 测试放哪

`tests/` 目录镜像 `src/crossview/`：

```text
tests/schema/          ↔ src/crossview/schema/
tests/core/geometry/   ↔ src/crossview/core/geometry/
tests/adaptors/        ↔ src/crossview/adaptors/
```

**新增一个模块，就在对应目录加 `test_<模块名>.py`。**

### 三类测试

| 类型 | 测什么 | 需要数据吗 |
|---|---|---|
| 单元测试 | 纯函数算得对不对（几何、路由、指标） | 不需要，用合成数据 |
| 契约测试 | 接口返回的形状对不对、序列化能否往返 | 不需要 |
| golden 测试 | 整条流程行为有没有变 | 需要小样本，见 `tests/fixtures/README.md` |

### 测试红了怎么办

```bash
git stash            # 先确认是不是自己改出来的
python -m pytest tests -q
git stash pop
```

- 还是红 → 这个 bug 本来就在，先别管，专注自己的改动
- 变绿 → 是你改出来的，修代码

**永远不要**为了变绿去改断言、跳过用例、删测试。那叫把问题藏起来，不叫修。

---

## 3. PR 与 review

- **一个 PR 只做一件事**。如果你说不清它做了什么，就该拆
- 标题一句话说清做了什么，不要写"修改"、"更新"这种
- 被要求改时，直接在同一个分支上继续提交，PR 会自动更新，不用重开

---

## 4. 遇到冲突

推送被拒（`non-fast-forward`）说明远端有你没有的提交：

```bash
git pull --rebase origin main
```

如果报冲突：

1. `git status` 看哪些文件冲突（标记为 `both modified`）
2. 打开文件，找 `<<<<<<<` / `=======` / `>>>>>>>`，手工保留正确内容，删掉标记
3. `git add <冲突文件>`
4. `git rebase --continue`

**不要用 `git push --force`**，那会覆盖别人的提交。

---

## 5. 常见报错对照

| 报错 | 原因 | 解决 |
|---|---|---|
| `Permission denied (publickey)` | SSH key 没加到 GitHub | 重做 0.3 |
| `Support for password authentication was removed` | 用了账号密码 | 改用 token 或 SSH |
| `non-fast-forward` | 远端有你没有的提交 | `git pull --rebase origin main` |
| `CONFLICT (content)` | 同一个文件两边都改了 | 按第 4 节手工解决 |
| `fatal: not a git repository` | 不在仓库目录里 | `cd` 到仓库根 |
| `ModuleNotFoundError: crossview` | 没装包或没激活 venv | `pip install -e ".[dev]"`，确认 venv 已激活 |
| `check.py` 红了 | 分别看 ruff / mypy / pytest 哪一步 | 见第 6 节 |

---

## 6. check.py 红了怎么办

按顺序看是哪一步失败：

```text
[OK] ruff check      格式或明显的代码问题
[OK] ruff format     缩进、空行、换行不符合统一格式
[OK] mypy            类型标注不一致
[OK] pytest          测试失败
```

- **ruff / format**：直接 `ruff check --fix src tests scripts tools && ruff format src tests scripts tools`，多数能自动修
- **mypy**：只在 `schema/` 和 `registry.py` 上跑，报错通常是类型标注写错了
- **pytest**：按第 2 节判断是自己改坏的还是本来就有

修不了就把完整报错贴给 Agent，让它定位——但**最终判断对不对是你的事**。

---

## 7. 不该做的事

```text
❌ 直接往 main 推（约定上禁止，等分支保护开了会被硬拦）
❌ 用 git push --force
❌ 提交数据、权重、实验产物（outputs/ 和 experiments/ 已忽略，别绕开）
❌ 一次 PR 改五个模块
❌ 为了让测试过而放宽断言
❌ 把密钥、密码写进任何文件
```

---

## 8. 文档里没覆盖的情况

照文档做。文档没写的，**先问负责人，讨论完把结论补进 `AGENTS.md` 或这份文件**，
不要自己发明一条新规则——四个人各自记一套，等于没有规则。

---

## 9. 卡住了找谁

| 问题 | 找谁 |
|---|---|
| 权限、仓库设置、CI | 仓库 owner |
| 分工、进度、要不要做某件事 | 项目负责人（A 角色） |
| 算法、实验设计 | 对应算法负责人（B/C/D） |

自己先试两次；两次不行就带着"试了什么、报错是什么"去问，不要闷头硬试。

---

详细的工程规则见 [AGENTS.md](AGENTS.md)，文档分类见 [docs/README.md](docs/README.md)。
