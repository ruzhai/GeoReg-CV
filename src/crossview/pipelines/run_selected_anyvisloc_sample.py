"""Run the official AnyVisLoc baseline for one explicitly selected sample.

The official project is imported and patched in memory with a filtered dataset
class. No files under D:/GD/Benchmark are modified.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

from crossview.pipelines.run_anyvisloc_baseline import build_command


def _set_option(arguments: list[str], name: str, values: list[str]) -> None:
    """Replace a single-value option or append it when it is absent."""
    if name in arguments:
        index = arguments.index(name)
        arguments[index + 1 : index + 2] = values
    else:
        arguments.extend([name, *values])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run AnyVisLoc localization for one selected NPZ sample."
    )
    parser.add_argument("--sample-id", required=True, help="Sample ID, for example L01_0120.")
    parser.add_argument(
        "--scene",
        default=None,
        help="Optional scene filter, for example Scene_01. Recommended for unambiguous selection.",
    )
    parser.add_argument(
        "--config",
        default="D:/GeoReg-CV/configs/anyvisloc_baseline.yaml",
        help="GeoReg-CV baseline YAML configuration.",
    )
    parser.add_argument(
        "--save-dir",
        default="D:/GeoReg-CV/experiments/selected_samples",
        help="Root directory for selected-sample results.",
    )
    parser.add_argument("--strategy", choices=["Top1", "Topn_opt"], default=None)
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Actual number of candidates matched by Topn_opt (writes a runtime YAML copy).",
    )
    parser.add_argument("--retrieval-k", type=int, default=None)
    parser.add_argument("--match-keypoints", type=int, default=None)
    parser.add_argument("--resize-ratio", type=float, default=None)
    parser.add_argument(
        "--visualize", action="store_true", help="Save retrieval and PnP visualizations."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate selection and print arguments only."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sample_id = Path(args.sample_id).stem
    config_path = Path(args.config)
    command, benchmark_root = build_command(config_path)

    dataset_root = Path(command[command.index("--dataset_root") + 1])
    pattern = f"{sample_id}.npz"
    candidates = sorted(dataset_root.rglob(pattern))
    if args.scene:
        candidates = [path for path in candidates if path.parent.name == args.scene]

    if not candidates:
        scene_text = f" in {args.scene}" if args.scene else ""
        raise FileNotFoundError(
            f"Sample {sample_id}{scene_text} was not found under {dataset_root}."
        )
    if len(candidates) > 1:
        matches = "\n".join(f"  - {path}" for path in candidates)
        raise RuntimeError(
            f"Sample ID {sample_id} is ambiguous. Pass --scene to choose one:\n{matches}"
        )

    selected_path = candidates[0]
    selected_scene = selected_path.parent.name
    output_root = Path(args.save_dir) / selected_scene / sample_id
    output_root.mkdir(parents=True, exist_ok=True)

    # Drop the executable and script name produced by build_command(). The
    # remaining arguments are consumed directly by the imported official main().
    official_args = command[2:]
    _set_option(official_args, "--save_dir", [str(output_root)])
    _set_option(official_args, "--limit", ["1"])
    if args.top_n is not None:
        if args.top_n < 1:
            raise ValueError("--top-n must be at least 1.")
        yaml_index = official_args.index("--yaml") + 1
        source_yaml = Path(official_args[yaml_index])
        with source_yaml.open("r", encoding="utf-8") as file:
            runtime_config = yaml.safe_load(file)
        runtime_config["RETRIEVAL_TOPN"] = int(args.top_n)
        runtime_yaml = output_root / f"runtime_config_top{args.top_n}.yaml"
        with runtime_yaml.open("w", encoding="utf-8") as file:
            yaml.safe_dump(runtime_config, file, sort_keys=False, allow_unicode=True)
        official_args[yaml_index] = str(runtime_yaml)
    if args.strategy:
        _set_option(official_args, "--strategy", [args.strategy])
    if args.retrieval_k is not None:
        _set_option(official_args, "--retrieval_k", [str(args.retrieval_k)])
    if args.match_keypoints is not None:
        _set_option(official_args, "--match_keypoints", [str(args.match_keypoints)])
    if args.resize_ratio is not None:
        if not 0 < args.resize_ratio <= 1:
            raise ValueError("--resize-ratio must be in (0, 1].")
        _set_option(official_args, "--resize_ratio", [str(args.resize_ratio)])
    if args.scene:
        official_args.extend(["--scenes", selected_scene])
    if args.visualize:
        official_args.append("--visualize")

    print(f"Selected sample: {selected_path}")
    print(f"Output root: {output_root}")
    print("Official arguments:")
    print(" ".join(official_args))
    if args.dry_run:
        return

    benchmark_root = benchmark_root.resolve()
    sys.path.insert(0, str(benchmark_root))
    os.chdir(benchmark_root)

    import run_avl  # pylint: disable=import-outside-toplevel

    original_dataset = run_avl.AnyVisLocNPZDataset

    class SelectedSampleDataset(original_dataset):
        def __init__(self, *dataset_args, **dataset_kwargs):
            super().__init__(*dataset_args, **dataset_kwargs)
            selected = [
                (path, scene)
                for path, scene in zip(self.samples, self.sample_scene, strict=False)
                if path.stem == sample_id and scene == selected_scene
            ]
            if len(selected) != 1:
                raise RuntimeError(
                    f"Expected exactly one dataset item for {selected_scene}/{sample_id}, "
                    f"found {len(selected)}."
                )
            self.samples = [selected[0][0]]
            self.sample_scene = [selected[0][1]]

    run_avl.AnyVisLocNPZDataset = SelectedSampleDataset
    sys.argv = [str(benchmark_root / "run_avl.py"), *official_args]
    run_avl.main()


if __name__ == "__main__":
    main()
