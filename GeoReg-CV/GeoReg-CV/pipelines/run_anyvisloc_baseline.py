import argparse
import copy
import subprocess
from pathlib import Path

import yaml


def build_command(config_path: Path) -> tuple[list[str], Path]:
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    avl = cfg["anyvisloc"]
    run = cfg["run"]

    anyvisloc_root = Path(avl["root"])
    save_dir = Path(avl["save_dir"])
    save_dir.mkdir(parents=True, exist_ok=True)

    official_yaml = Path(avl["config"])
    runtime_yaml = official_yaml
    if run.get("top_n") is not None:
        top_n = int(run["top_n"])
        if top_n < 1:
            raise ValueError("run.top_n must be at least 1")
        with official_yaml.open("r", encoding="utf-8") as f:
            runtime_cfg = copy.deepcopy(yaml.safe_load(f))
        runtime_cfg["RETRIEVAL_TOPN"] = top_n
        runtime_cfg["RETRIEVAL_IMG_NUM"] = top_n
        runtime_yaml = save_dir / "runtime_anyvisloc_config.yaml"
        with runtime_yaml.open("w", encoding="utf-8") as f:
            yaml.safe_dump(runtime_cfg, f, sort_keys=False, allow_unicode=True)

    command = [
        "python",
        "run_avl.py",
        "--dataset_root",
        avl["dataset_root"],
        "--yaml",
        str(runtime_yaml),
        "--save_dir",
        str(save_dir),
        "--reference_mode",
        run["reference_mode"],
        "--pose_priori",
        run["pose_priori"],
        "--strategy",
        run["strategy"],
        "--PnP_method",
        run["pnp_method"],
        "--match_keypoints",
        str(run["match_keypoints"]),
        "--retrieval_k",
        str(run["retrieval_k"]),
        "--success_thresholds",
        *[str(v) for v in run["success_thresholds"]],
        "--device",
        run["device"],
    ]

    if run.get("resize_ratio") is not None:
        command.extend(["--resize_ratio", str(run["resize_ratio"])])
    if run.get("patch_scale") is not None:
        command.extend(["--patch_scale", str(run["patch_scale"])])
    if run.get("scenes"):
        command.extend(["--scenes", *[str(scene) for scene in run["scenes"]]])
    if run.get("visualize", False):
        command.append("--visualize")
    elif "visualize" in run:
        command.append("--no-visualize")

    if run.get("limit") is not None:
        command.extend(["--limit", str(run["limit"])])

    return command, anyvisloc_root


def main() -> None:
    parser = argparse.ArgumentParser(description="Run official AnyVisLoc baseline from GeoReg-CV.")
    parser.add_argument("--config", default="D:/GeoReg-CV/configs/anyvisloc_baseline.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Print command without executing.")
    args = parser.parse_args()

    command, cwd = build_command(Path(args.config))
    print("Working directory:", cwd)
    print("Command:")
    print(" ".join(command))

    if not args.dry_run:
        subprocess.run(command, cwd=str(cwd), check=True)


if __name__ == "__main__":
    main()
