"""结果产物落盘与输出流：匹配点、仿真交换格式、CSV/JSON 汇总。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


class TeeStream:
    """Write progress to the Windows console and a UTF-8 log file."""

    def __init__(self, console, log_file):
        self.console = console
        self.log_file = log_file
        self.encoding = getattr(console, "encoding", None) or "utf-8"

    def write(self, text: str) -> int:
        safe_text = text.encode(self.encoding, errors="replace").decode(self.encoding)
        self.console.write(safe_text)
        self.log_file.write(text)
        return len(text)

    def flush(self) -> None:
        self.console.flush()
        self.log_file.flush()

    def isatty(self) -> bool:
        return bool(getattr(self.console, "isatty", lambda: False)())


def float_or_none(value):
    if value in (None, ""):
        return None
    return float(value)


def save_match_records(run_dir: Path, records: list[dict]) -> tuple[list[str], list[dict]]:
    data_dir = run_dir / "match_data"
    paths = []
    summaries = []
    if records:
        data_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        rank = int(record["candidate_rank"])
        path = data_dir / f"candidate_{rank:02d}_roma_matches.npz"
        dense = record.get("dense_center_correspondence") or {}
        np.savez_compressed(
            path,
            query_points_px=record["query_points_px"],
            reference_patch_points_px=record["reference_patch_points_px"],
            reference_map_points_px=record["reference_map_points_px"],
            world_points_xyz=record["world_points_xyz"],
            roma_confidence=record["roma_confidence"],
            map_resolution=record["map_resolution"],
            map_origin_local=record["map_origin_local"],
            dense_reference_patch_uv=np.asarray(
                [dense.get("reference_patch_u", np.nan), dense.get("reference_patch_v", np.nan)],
                dtype=np.float32,
            ),
            dense_reference_map_uv=np.asarray(
                [dense.get("reference_map_u", np.nan), dense.get("reference_map_v", np.nan)],
                dtype=np.float32,
            ),
            dense_world_xyz=np.asarray(
                [dense.get("x", np.nan), dense.get("y", np.nan), dense.get("z", np.nan)],
                dtype=np.float32,
            ),
            dense_forward_certainty=np.float32(dense.get("forward_certainty", np.nan)),
            dense_backward_certainty=np.float32(dense.get("backward_certainty", np.nan)),
            dense_cycle_error_px=np.float32(dense.get("cycle_error_px", np.nan)),
        )
        paths.append(str(path))
        summaries.append(
            {
                "candidate_rank": rank,
                "saved_matches": int(len(record["query_points_px"])),
                "dense_center_available": bool(dense.get("success")),
                "file": str(path),
            }
        )
    return paths, summaries


def write_unreal_result(run_dir: Path, payload: dict) -> Path:
    experiment = payload.get("experimental_center_estimation", {})
    unreal_payload = {
        "schema": "GeoReg-CV.UnrealCenterResult.v1",
        "scene": payload["scene_name"],
        "sample_id": payload["sample_id"],
        "input_center_gt": payload.get("input_image_center_ground_point"),
        "direct_center_point": experiment.get("direct_center_point"),
        "pnp_center_point": experiment.get("pnp_center_point"),
        "final_center_point": experiment.get("final_center_point"),
        "center_method": experiment.get("center_method"),
        "center_confidence": experiment.get("center_confidence"),
        "center_error_m": experiment.get("center_error_m"),
        "direct_vs_pnp_distance_m": experiment.get("direct_vs_pnp_distance_m"),
        "pnp_numerical_success": experiment.get("pnp_numerical_success"),
        "pnp_physically_valid": experiment.get("pnp_physically_valid"),
        "adaptive_route": payload.get("adaptive_strategy", {}).get("route"),
        "top1_inliers": payload.get("adaptive_strategy", {}).get("top1_best_inliers"),
        "matching_total_s": payload.get("timing", {}).get("matching_total_s"),
        "total_s": payload.get("timing", {}).get("online_pipeline_wall_time_s"),
        "artifacts": payload.get("artifacts", {}),
    }
    path = run_dir / "unreal_result.json"
    path.write_text(json.dumps(unreal_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_outputs(run_dir: Path, payload: dict) -> None:
    unreal_path = write_unreal_result(run_dir, payload)
    payload.setdefault("artifacts", {})["unreal_result"] = str(unreal_path)
    json_path = run_dir / "cda_result.json"
    csv_path = run_dir / "cda_result.csv"
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    flat = {
        "method": payload["method"],
        "execution_mode": payload["execution_mode"],
        "scene_name": payload["scene_name"],
        "sample_id": payload["sample_id"],
        **payload["localization"],
        **payload["adaptive_strategy"],
        **payload["timing"],
        "center_ground_success": payload.get("image_center_ground_point", {}).get("success"),
        "center_ground_x": payload.get("image_center_ground_point", {}).get("x"),
        "center_ground_y": payload.get("image_center_ground_point", {}).get("y"),
        "center_ground_z": payload.get("image_center_ground_point", {}).get("z"),
        "center_ground_reason": payload.get("image_center_ground_point", {}).get("reason"),
        "input_center_gt_x": payload.get("input_image_center_ground_point", {}).get("x"),
        "input_center_gt_y": payload.get("input_image_center_ground_point", {}).get("y"),
        "input_center_gt_z": payload.get("input_image_center_ground_point", {}).get("z"),
        "output_corresponding_x": payload.get("output_corresponding_point", {}).get("x"),
        "output_corresponding_y": payload.get("output_corresponding_point", {}).get("y"),
        "output_corresponding_z": payload.get("output_corresponding_point", {}).get("z"),
        "center_correspondence_error_m": payload.get("center_correspondence_error", {}).get(
            "horizontal_error_m"
        ),
        "center_method": payload.get("experimental_center_estimation", {}).get("center_method"),
        "center_confidence": payload.get("experimental_center_estimation", {}).get(
            "center_confidence"
        ),
        "direct_center_error_m": payload.get("experimental_center_estimation", {}).get(
            "direct_center_error_m"
        ),
        "hybrid_center_error_m": payload.get("experimental_center_estimation", {}).get(
            "center_error_m"
        ),
        "candidate_inliers": json.dumps(payload["candidate_inliers"]),
        "result_pkl": payload["artifacts"]["result_pkl"],
        "log": payload["artifacts"]["log"],
    }
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(flat.keys()))
        writer.writeheader()
        writer.writerow(flat)
    print(f"CDA result JSON: {json_path}")
    print(f"CDA result CSV: {csv_path}")
