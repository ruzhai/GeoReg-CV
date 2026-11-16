# 契约说明

契约是三条并行开发线之间**唯一的协调机制**。它不在文档里，在代码里。

## 五类契约

| 契约 | 文件 | 约定什么 | 谁最常碰到 |
|---|---|---|---|
| 结果 | `schema/records.py` | 一次配准的输出长什么样 | 所有人 |
| 输入 | `schema/samples.py` | 数据集适配器必须产出什么 | 数据集、匹配器 |
| 配置 | `schema/configs.py` | 实验怎么配置、路径从哪来 | 跑实验的人 |
| 枚举 | `schema/enums.py` | 路由、失败原因、坐标系 | 路由、分析 |
| 接口 | `schema/interfaces.py` | 各阶段的函数签名 | 新增方法的实现者 |

## 三条使用规则

1. **跨模块传数据必须用契约模型**，不允许裸 dict。
2. **加字段可以直接加**，但要给默认值；**改语义或删字段必须升 `schema_version`**。
3. 改了 schema 就跑 `pytest tests/schema`，并重新导出：

```bash
python scripts/export_schemas.py
```

导出的 JSON Schema 在 `docs/schema/`，MATLAB 侧读它做字段校验。

## 为什么不能用 dict

- dict 的字段名没有校验，改错了要到运行时才报，而且报的是 KeyError，看不出是契约变了。
- dict 没有默认值，新增字段时所有旧调用点都会崩。
- dict 无法导出 schema，跨语言的那一端只能靠口头约定。

## 版本号怎么用

```python
class GeoRegistrationRecord(BaseModel):
    schema_version: str = SCHEMA_VERSION
```

读取历史结果时先看版本号：

- 同一个大版本 → 直接读，缺的字段用默认值。
- 大版本不同 → 走迁移函数，不要硬读。

## 坐标系与单位

`frame` 和 `unit` 必须显式写在结果里。缺了它们，一个数字既可能是米也可能是像素，而且**不会报错**。
