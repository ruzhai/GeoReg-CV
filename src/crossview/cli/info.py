"""安装自检：不需要数据、不需要 GPU。"""

from __future__ import annotations

import crossview
from crossview import registry
from crossview.schema import SCHEMA_VERSION


def main() -> None:
    print(f"crossview {crossview.__version__}  (schema {SCHEMA_VERSION})")
    print(f"包路径: {crossview.__file__}")

    kinds = ["retriever", "matcher", "locator", "backbone"]
    print("\n已注册组件:")
    for kind in kinds:
        names = registry.available(kind)
        print(f"  {kind:10} {', '.join(names) if names else '（空）'}")


if __name__ == "__main__":
    main()
