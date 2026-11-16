"""统一的本地检查入口：lint -> format -> type -> test。

用法：
    python scripts/check.py            # 全部检查
    python scripts/check.py --fast     # 只跑 lint + test
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(name: str, args: list[str]) -> bool:
    print(f"\n=== {name} ===")
    result = subprocess.run(args, cwd=ROOT)
    if result.returncode != 0:
        print(f"[FAIL] {name}")
        return False
    print(f"[OK] {name}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="跳过类型检查")
    args = parser.parse_args()

    py = sys.executable
    checks = [
        ("ruff check", [py, "-m", "ruff", "check", "src", "tests"]),
        ("ruff format", [py, "-m", "ruff", "format", "--check", "src", "tests"]),
    ]
    if not args.fast:
        checks.append(("mypy", [py, "-m", "mypy"]))
    checks.append(("pytest", [py, "-m", "pytest", "-m", "not gpu and not slow"]))

    failed = [name for name, cmd in checks if not run(name, cmd)]
    if failed:
        print(f"\n失败项：{', '.join(failed)}")
        return 1
    print("\n全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
