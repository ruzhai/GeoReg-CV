"""Golden 测试：冻结一组样本的输入与期望输出，检测行为是否被意外改动。

真正跑流水线需要数据集和权重，所以这里只做结构校验。
把夹具放到 tests/fixtures/golden/<case>/ 后，本测试会自动开始检查。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
REQUIRED_KEYS = {"pred", "error_m", "route"}


def golden_cases() -> list[Path]:
    return sorted(GOLDEN_DIR.glob("*/expected.json"))


def test_golden_cases_are_well_formed():
    cases = golden_cases()
    if not cases:
        pytest.skip("尚未放置 golden 夹具，见 tests/fixtures/README.md")

    for case in cases:
        data = json.loads(case.read_text(encoding="utf-8"))
        missing = REQUIRED_KEYS - data.keys()
        assert not missing, f"{case.parent.name} 缺少字段：{missing}"
        assert isinstance(data["error_m"], int | float)
