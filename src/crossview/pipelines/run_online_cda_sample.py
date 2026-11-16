"""Single-process online CDA-FastReg for one AnyVisLoc sample.

Models are initialized once. Retrieval is executed once, then the confidence-
driven cascade evaluates Top1, candidate 2, and candidates 3..5 only when
needed. The official AnyVisLoc
project is imported but never modified.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import yaml

from crossview.core.routing.adaptive import (  # noqa: E402
    AdaptiveRegistrationPolicy,
    RegistrationConfidence,
)
from crossview.imaging.direct_center import (  # noqa: E402
    estimate_dense_center,
    estimate_direct_center,
    point_distance,
)
from crossview.imaging.geolocation import (  # noqa: E402
    center_correspondence_error,
    locate_ground_truth_image_center_on_dsm,
)
from crossview.imaging.physical_validity import evaluate_pnp_physical_validity  # noqa: E402

# Shared by the single-sample and batch entry points. The key includes the
# official config and device so incompatible model instances are never mixed.
_ONLINE_MODEL_CACHE: dict[tuple, dict] = {}


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run single-process online CDA-FastReg for one AnyVisLoc sample."
    )
    parser.add_argument("--sample-id", required=True, help="For example L01_0120.")
    parser.add_argument("--scene", required=True, help="For example Scene_01.")
    parser.add_argument("--config", default="D:/GeoReg-CV/configs/anyvisloc_baseline.yaml")
    parser.add_argument("--output-root", default="D:/GeoReg-CV/outputs/online_cda")
    parser.add_argument("--threshold", type=int, default=1000)
    parser.add_argument("--fallback-topk", type=int, choices=[2, 5], default=2)
    cascade = parser.add_mutually_exclusive_group()
    cascade.add_argument(
        "--cascade-top5",
        dest="cascade_top5",
        action="store_true",
        help="Escalate an unreliable Top2 result to candidates 3..5.",
    )
    cascade.add_argument(
        "--no-cascade-top5",
        dest="cascade_top5",
        action="store_false",
        help="Disable Top2 to Top5 escalation.",
    )
    parser.set_defaults(cascade_top5=True)
    parser.add_argument("--match-keypoints", type=int, default=1500)
    parser.add_argument("--resize-ratio", type=float, default=0.3)
    parser.add_argument("--patch-scale", type=float, default=1.0)
    direct = parser.add_mutually_exclusive_group()
    direct.add_argument("--direct-center", dest="direct_center", action="store_true")
    direct.add_argument("--no-direct-center", dest="direct_center", action="store_false")
    parser.set_defaults(direct_center=True)
    parser.add_argument("--center-radius", type=float, default=160.0)
    parser.add_argument("--center-confidence-threshold", type=float, default=0.10)
    parser.add_argument("--center-cycle-threshold-px", type=float, default=2.0)
    parser.add_argument("--pnp-min-clearance-m", type=float, default=1.0)
    parser.add_argument("--pnp-max-clearance-m", type=float, default=2000.0)
    parser.add_argument("--pnp-min-inlier-coverage", type=float, default=0.005)
    parser.add_argument(
        "--center-execution-mode",
        choices=["direct_first", "evaluation_both", "pnp_only"],
        default="direct_first",
        help="direct_first skips PnP when RoMa center confidence is high; evaluation_both runs both for analysis.",
    )
    visualization = parser.add_mutually_exclusive_group()
    visualization.add_argument("--visualize", dest="visualize", action="store_true")
    visualization.add_argument("--no-visualize", dest="visualize", action="store_false")
    parser.set_defaults(visualize=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _load_wrapper_config(path: Path) -> tuple[dict, dict]:
    with path.open("r", encoding="utf-8") as file:
        wrapper = yaml.safe_load(file)
    return wrapper["anyvisloc"], wrapper["run"]


def _build_official_options(args, benchmark_root: Path, run_config: dict) -> argparse.Namespace:
    selectable_dir = benchmark_root / "Matching_Models" / "Sparse_matchers"
    return argparse.Namespace(
        reference_mode=run_config.get("reference_mode", "aerial"),
        pose_priori=run_config.get("pose_priori", "yp"),
        strategy="Top1",
        PnP_method=run_config.get("pnp_method", "P3P"),
        resize_ratio=float(args.resize_ratio),
        device=run_config.get("device", "cuda"),
        match_keypoints=int(args.match_keypoints),
        selectable_code_dir=str(selectable_dir),
        selectable_module="selectable_sparse_matcher",
        gim_lg_ckpt=str(selectable_dir / "weights" / "gim_lightglue_100h.ckpt"),
        minima_lg_ckpt=str(selectable_dir / "weights" / "minima_lightglue.pth"),
        patch_scale=float(args.patch_scale),
        min_patch_size_m=0.0,
        max_patch_size_m=0.0,
        visualize=bool(args.visualize),
        draw_pnp_inlier_ratio=0.1,
        draw_pnp_inlier_seed=0,
        ref_feature_cache_dir=None,
        disable_ref_feature_cache=False,
        pnp_reproj_error=8.0,
        pnp_iterations=2000,
        pnp_confidence=0.999,
        retrieval_k=int(args.fallback_topk),
        pdm_lambda=6.0,
        pdm_alpha=0.9,
    )


def _select_sample(dataset, sample_id: str, scene: str):
    matches = [
        index
        for index, (path, sample_scene) in enumerate(
            zip(dataset.samples, dataset.sample_scene, strict=False)
        )
        if path.stem == sample_id and sample_scene == scene
    ]
    if not matches:
        raise FileNotFoundError(
            f"Sample {scene}/{sample_id} was not found in the AnyVisLoc dataset."
        )
    if len(matches) != 1:
        raise RuntimeError(f"Expected one sample for {scene}/{sample_id}, found {len(matches)}.")
    return dataset[matches[0]]


def _float_or_none(value):
    if value in (None, ""):
        return None
    return float(value)


def _save_match_records(run_dir: Path, records: list[dict]) -> tuple[list[str], list[dict]]:
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


def _write_unreal_result(run_dir: Path, payload: dict) -> Path:
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


def _save_outputs(run_dir: Path, payload: dict) -> None:
    unreal_path = _write_unreal_result(run_dir, payload)
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


def _run(args: argparse.Namespace, run_dir: Path) -> dict:
    anyvisloc_config, run_config = _load_wrapper_config(Path(args.config))
    benchmark_root = Path(anyvisloc_config["root"]).resolve()
    dataset_root = Path(anyvisloc_config["dataset_root"]).resolve()
    official_yaml = Path(anyvisloc_config["config"]).resolve()
    if str(benchmark_root) not in sys.path:
        sys.path.insert(0, str(benchmark_root))

    from avl_data import AnyVisLocNPZDataset

    with official_yaml.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    config["DEVICE"] = run_config.get("device", "cuda")
    retrieval_topn = 5 if args.cascade_top5 else int(args.fallback_topk)
    config["RETRIEVAL_TOPN"] = retrieval_topn
    opt = _build_official_options(args, benchmark_root, run_config)
    opt.retrieval_k = retrieval_topn
    sample_id = Path(args.sample_id).stem

    dataset = AnyVisLocNPZDataset(
        root=str(dataset_root),
        scenes=[args.scene],
        load_reference=False,
        cache_reference=True,
        recursive=True,
    )
    sample = _select_sample(dataset, sample_id, args.scene)
    selected_path = Path(sample["npz_path"])
    print(f"Selected sample: {selected_path}")
    print(f"Run directory: {run_dir}")
    if args.dry_run:
        return {
            "dry_run": True,
            "sample": str(selected_path),
            "fallback_topk": args.fallback_topk,
            "cascade_top5": args.cascade_top5,
            "retrieval_topn": retrieval_topn,
        }

    from avl_utils import (
        Match2Pos_all_anyvisloc,
        anyvisloc_sample_to_truepos,
        build_anyvisloc_reference_view,
        dumpRotateImage,
        estimate_pose_from_match_record_anyvisloc,
        matching_init,
        pos2error_anyvisloc,
        retrieval_all_anyvisloc,
        retrieval_init,
        save_data,
        tensor_rgb_to_bgr_uint8,
    )
    from run_avl import _retrieval_metrics_from_ratios

    pipeline_start = time.perf_counter()
    init_start = time.perf_counter()
    retrieval_method = config["RETRIEVAL_METHODS"][0]
    matching_method = config["MATCHING_METHODS"][0]
    cache_key = (
        str(official_yaml),
        str(opt.device),
        retrieval_method,
        matching_method,
    )
    if cache_key in _ONLINE_MODEL_CACHE:
        method_dict = _ONLINE_MODEL_CACHE[cache_key]
        initialization_time = 0.0
        print("Reusing cached retrieval/matching models.")
    else:
        method_dict = retrieval_init({"retrieval_method": retrieval_method}, config)
        method_dict["matching_method"] = matching_method
        method_dict = matching_init(method_dict, opt, config)
        _ONLINE_MODEL_CACHE[cache_key] = method_dict
        initialization_time = time.perf_counter() - init_start

    prepare_start = time.perf_counter()
    true_pos = anyvisloc_sample_to_truepos(sample)
    K = sample["K"].detach().cpu().numpy().astype(np.float32)
    dist = sample["dist"].detach().cpu().numpy().astype(np.float32)
    observer_image = tensor_rgb_to_bgr_uint8(sample["image"])
    view = build_anyvisloc_reference_view(sample, opt.reference_mode)
    reference_map_original = view["map"]
    dsm_map = view["dsm"]
    if opt.pose_priori == "yp":
        reference_map, rotation = dumpRotateImage(reference_map_original, true_pos["yaw"])
    else:
        reference_map = reference_map_original
        rotation = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32)
    reference_prepare_time = time.perf_counter() - prepare_start

    opt._current_scene_name = args.scene
    opt._current_sample_id = sample_id
    retrieval_start = time.perf_counter()
    (
        retrieval_order,
        row_starts,
        col_starts,
        pde_list,
        patch_h,
        patch_w,
        fine_scale,
        retrieval_model_time,
    ) = retrieval_all_anyvisloc(
        reference_map,
        observer_image,
        true_pos,
        view["map_resolution"],
        view["map_origin_local"],
        rotation,
        str(run_dir / "retrieval"),
        opt,
        config,
        method_dict,
    )
    retrieval_wall_time = time.perf_counter() - retrieval_start
    if len(row_starts) == 0:
        raise RuntimeError("Retrieval produced no reference candidates.")

    match_records = []
    top1_start = time.perf_counter()
    opt.strategy = "Top1"
    center_execution_mode = getattr(args, "center_execution_mode", "direct_first")
    direct_first_enabled = bool(
        getattr(args, "direct_center", True) and center_execution_mode == "direct_first"
    )
    top1_xyz, top1_inliers, top1_match_times, top1_pnp_times = Match2Pos_all_anyvisloc(
        opt,
        config,
        observer_image,
        fine_scale,
        K,
        reference_map,
        dsm_map,
        row_starts[:1],
        col_starts[:1],
        patch_h,
        patch_w,
        str(run_dir / "top1"),
        method_dict,
        rotation,
        view["map_resolution"],
        view["map_origin_local"],
        view["dsm_resolution"],
        view["dsm_origin_local"],
        dist=dist,
        truePos=true_pos,
        match_records=match_records,
        candidate_rank_offset=0,
        defer_pnp=direct_first_enabled,
    )
    dense_top1 = (
        estimate_dense_center(
            match_records[0],
            min_center_confidence=float(getattr(args, "center_confidence_threshold", 0.10)),
            max_cycle_error_px=float(getattr(args, "center_cycle_threshold_px", 2.0)),
        )
        if getattr(args, "direct_center", True) and match_records
        else {
            "success": False,
            "reason": "direct center disabled or no Top1 match record",
            "method": "roma_dense_center",
            "x": None,
            "y": None,
            "z": None,
            "center_confidence": 0.0,
            "high_confidence": False,
        }
    )
    dense_top1["candidate_rank"] = 1
    direct_accepted = bool(direct_first_enabled and dense_top1.get("high_confidence"))
    if direct_first_enabled and not direct_accepted and match_records:
        pnp_start = time.perf_counter()
        solved_xyz, solved_inliers, _ = estimate_pose_from_match_record_anyvisloc(
            match_records[0], K, dist, opt
        )
        pnp_elapsed = time.perf_counter() - pnp_start
        top1_xyz = [solved_xyz]
        top1_inliers = [solved_inliers]
        if top1_pnp_times:
            top1_pnp_times[0] = pnp_elapsed
        else:
            top1_pnp_times = [pnp_elapsed]
        print(
            "Dense center confidence insufficient; reused the same RoMa matches for PnP "
            f"({dense_top1.get('center_confidence', 0.0):.3f}, "
            f"cycle={dense_top1.get('cycle_error_px')})."
        )
    elif direct_accepted:
        print(
            "Dense center accepted; PnP skipped "
            f"(confidence={dense_top1.get('center_confidence', 0.0):.3f}, "
            f"cycle={dense_top1.get('cycle_error_px'):.3f}px)."
        )
    top1_wall_time = time.perf_counter() - top1_start
    top1_best_inliers = int(max(top1_inliers) if top1_inliers else 0)
    top1_validation = (
        evaluate_pnp_physical_validity(
            top1_xyz[0],
            match_records[0] if match_records else None,
            K,
            dist,
            observer_image.shape[:2],
            dsm_map,
            view["dsm_resolution"],
            view["dsm_origin_local"],
            reprojection_threshold_px=float(opt.pnp_reproj_error),
            min_inlier_coverage_ratio=float(args.pnp_min_inlier_coverage),
            min_camera_clearance_m=float(args.pnp_min_clearance_m),
            max_camera_clearance_m=float(args.pnp_max_clearance_m),
        )
        if not direct_accepted and top1_xyz
        else None
    )
    top1_success = bool(
        top1_validation and top1_validation.get("physically_valid") and top1_best_inliers > 0
    )
    pnp_validations = [top1_validation] if top1_validation is not None else []
    xyz_list = list(top1_xyz)
    inliers_list = list(top1_inliers)
    match_times = list(top1_match_times)
    pnp_times = list(top1_pnp_times)
    fallback_wall_time = 0.0
    fallback_count = 0
    fallback_dir = None
    fallback_top5_dir = None
    policy = AdaptiveRegistrationPolicy(args.threshold, args.fallback_topk)
    top1_confidence = RegistrationConfidence(
        pnp_success=top1_success, best_inliers=top1_best_inliers
    )
    top2_confidence = top1_confidence
    decision = (
        SimpleNamespace(
            route=SimpleNamespace(value="direct_center_fast_path"),
            reason="RoMa dense center confidence passed; PnP and candidate fallback were skipped.",
            accepted_top1=True,
        )
        if direct_accepted
        else policy.decide(top1_confidence)
    )

    if not decision.accepted_top1:
        # First evaluate only candidate 2. This preserves the fast cascade:
        # candidates 3..5 are not matched unless Top2 is still unreliable.
        top2_count = min(2, len(row_starts))
        if top2_count > 1:
            fallback_method = dict(method_dict)
            fallback_method["retrieval_topn"] = 1
            opt.strategy = "Topn_opt"
            fallback_dir = run_dir / "fallback_candidates_2_to_2"
            fallback_start = time.perf_counter()
            extra_xyz, extra_inliers, extra_match_times, extra_pnp_times = Match2Pos_all_anyvisloc(
                opt,
                config,
                observer_image,
                fine_scale,
                K,
                reference_map,
                dsm_map,
                row_starts[1:top2_count],
                col_starts[1:top2_count],
                patch_h,
                patch_w,
                str(fallback_dir),
                fallback_method,
                rotation,
                view["map_resolution"],
                view["map_origin_local"],
                view["dsm_resolution"],
                view["dsm_origin_local"],
                dist=dist,
                truePos=true_pos,
                match_records=match_records,
                candidate_rank_offset=1,
            )
            fallback_wall_time += time.perf_counter() - fallback_start
            xyz_list.extend(extra_xyz)
            inliers_list.extend(extra_inliers)
            match_times.extend(extra_match_times)
            pnp_times.extend(extra_pnp_times)
            fallback_count += len(extra_xyz)
            top2_confidence = RegistrationConfidence(
                pnp_success=False,
                best_inliers=0,
            )
            while len(pnp_validations) < len(xyz_list):
                index = len(pnp_validations)
                pnp_validations.append(
                    evaluate_pnp_physical_validity(
                        xyz_list[index],
                        match_records[index] if index < len(match_records) else None,
                        K,
                        dist,
                        observer_image.shape[:2],
                        dsm_map,
                        view["dsm_resolution"],
                        view["dsm_origin_local"],
                        reprojection_threshold_px=float(opt.pnp_reproj_error),
                        min_inlier_coverage_ratio=float(args.pnp_min_inlier_coverage),
                        min_camera_clearance_m=float(args.pnp_min_clearance_m),
                        max_camera_clearance_m=float(args.pnp_max_clearance_m),
                    )
                )
            valid_top2_inliers = [
                int(inliers_list[index])
                for index, validation in enumerate(pnp_validations)
                if validation.get("physically_valid")
            ]
            top2_confidence = RegistrationConfidence(
                pnp_success=bool(valid_top2_inliers),
                best_inliers=max(valid_top2_inliers) if valid_top2_inliers else 0,
            )

        top2_confident = policy.evaluator.is_confident(top2_confidence)[0]
        if (args.cascade_top5 or args.fallback_topk == 5) and not top2_confident:
            top5_count = min(5, len(row_starts))
            if top5_count > 2:
                fallback_method = dict(method_dict)
                fallback_method["retrieval_topn"] = top5_count - 2
                opt.strategy = "Topn_opt"
                fallback_top5_dir = run_dir / "fallback_candidates_3_to_5"
                fallback_start = time.perf_counter()
                extra_xyz, extra_inliers, extra_match_times, extra_pnp_times = (
                    Match2Pos_all_anyvisloc(
                        opt,
                        config,
                        observer_image,
                        fine_scale,
                        K,
                        reference_map,
                        dsm_map,
                        row_starts[2:top5_count],
                        col_starts[2:top5_count],
                        patch_h,
                        patch_w,
                        str(fallback_top5_dir),
                        fallback_method,
                        rotation,
                        view["map_resolution"],
                        view["map_origin_local"],
                        view["dsm_resolution"],
                        view["dsm_origin_local"],
                        dist=dist,
                        truePos=true_pos,
                        match_records=match_records,
                        candidate_rank_offset=2,
                    )
                )
                fallback_wall_time += time.perf_counter() - fallback_start
                xyz_list.extend(extra_xyz)
                inliers_list.extend(extra_inliers)
                match_times.extend(extra_match_times)
                pnp_times.extend(extra_pnp_times)
                fallback_count += len(extra_xyz)
                decision = policy.decide_cascade(top1_confidence, top2_confidence)
        elif args.cascade_top5:
            decision = policy.decide_cascade(top1_confidence, top2_confidence)

    print(f"CDA decision: {decision.route.value} ({decision.reason})")

    while len(pnp_validations) < len(xyz_list):
        index = len(pnp_validations)
        pnp_validations.append(
            evaluate_pnp_physical_validity(
                xyz_list[index],
                match_records[index] if index < len(match_records) else None,
                K,
                dist,
                observer_image.shape[:2],
                dsm_map,
                view["dsm_resolution"],
                view["dsm_origin_local"],
                reprojection_threshold_px=float(opt.pnp_reproj_error),
                min_inlier_coverage_ratio=float(args.pnp_min_inlier_coverage),
                min_camera_clearance_m=float(args.pnp_min_clearance_m),
                max_camera_clearance_m=float(args.pnp_max_clearance_m),
            )
        )
    pnp_numerical_success = any(v.get("pnp_solved") for v in pnp_validations)
    valid_xyz_list = []
    valid_inliers_list = []
    for item, inlier_count, validation in zip(
        xyz_list, inliers_list, pnp_validations, strict=False
    ):
        if validation.get("physically_valid"):
            valid_xyz_list.append(item)
            valid_inliers_list.append(int(inlier_count))
        else:
            invalid = dict(item)
            invalid.update(X=None, Y=None, Z=None, L=None, B=None, H=None)
            valid_xyz_list.append(invalid)
            valid_inliers_list.append(-1)
    raw_best_inliers = int(max(inliers_list) if inliers_list else 0)
    final_best_inliers = max(valid_inliers_list) if valid_inliers_list else 0
    final_best_inliers = max(int(final_best_inliers), 0)
    pred_loc, pred_error, location_errors, pnp_success, best_index = pos2error_anyvisloc(
        true_pos, valid_xyz_list, valid_inliers_list
    )
    best_validation = (
        pnp_validations[best_index]
        if best_index is not None and 0 <= int(best_index) < len(pnp_validations)
        else None
    )
    pnp_center_point = (
        dict(best_validation["center_point"])
        if best_validation and best_validation.get("physically_valid")
        else {
            "success": False,
            "reason": "no PnP candidate passed physical validity checks",
            "physical_failure_reasons": (
                best_validation.get("failure_reasons", []) if best_validation else []
            ),
        }
    )
    pnp_center_point["source"] = f"{opt.reference_mode}_dsm"
    input_image_center_ground_point = locate_ground_truth_image_center_on_dsm(
        sample["pose_c2w"].detach().cpu().numpy(),
        [true_pos["x"], true_pos["y"], true_pos["z"]],
        K,
        dist,
        observer_image.shape[:2],
        dsm_map,
        view["dsm_resolution"],
        view["dsm_origin_local"],
    )
    input_image_center_ground_point["source"] = f"{opt.reference_mode}_dsm"
    pnp_center_point["definition"] = "PnP-ray estimate corresponding to input-image center"
    pnp_center_error = center_correspondence_error(
        input_image_center_ground_point, pnp_center_point
    )
    # Retain the previous local-homography estimator only as an ablation in
    # evaluation_both mode.  It is not used by the cross-scene online decision.
    local_homography_candidates = []
    if getattr(args, "direct_center", True) and center_execution_mode == "evaluation_both":
        for match_record in match_records:
            estimate = estimate_direct_center(
                match_record,
                observer_image.shape[:2],
                dsm_map,
                view["dsm_resolution"],
                view["dsm_origin_local"],
                neighborhood_radius_px=float(getattr(args, "center_radius", 160.0)),
                min_center_confidence=float(getattr(args, "center_confidence_threshold", 0.70)),
            )
            estimate["candidate_rank"] = int(match_record["candidate_rank"])
            local_homography_candidates.append(estimate)
    direct_center_point = dense_top1
    direct_center_error = center_correspondence_error(
        input_image_center_ground_point, direct_center_point
    )
    direct_vs_pnp_distance = point_distance(direct_center_point, pnp_center_point)
    use_direct = bool(
        getattr(args, "direct_center", True)
        and center_execution_mode != "pnp_only"
        and direct_center_point.get("success")
        and direct_center_point.get("high_confidence")
    )
    final_center_point = direct_center_point if use_direct else pnp_center_point
    final_center_method = "roma_dense_center" if use_direct else "pnp_ray_fallback"
    output_corresponding_point = dict(final_center_point)
    output_corresponding_point["definition"] = (
        "final inferred reference point corresponding to input-image center"
    )
    final_center_error = center_correspondence_error(
        input_image_center_ground_point, final_center_point
    )
    experimental_center_estimation = {
        "status": "online_direct_first"
        if center_execution_mode == "direct_first"
        else center_execution_mode,
        "execution_mode": center_execution_mode,
        "center_method": final_center_method,
        "center_confidence": float(direct_center_point.get("center_confidence", 0.0)),
        "direct_center_point": direct_center_point,
        "pnp_center_point": pnp_center_point,
        "final_center_point": final_center_point,
        "direct_vs_pnp_distance_m": direct_vs_pnp_distance,
        "direct_center_error_m": direct_center_error.get("horizontal_error_m"),
        "pnp_center_error_m": pnp_center_error.get("horizontal_error_m"),
        "center_error_m": final_center_error.get("horizontal_error_m"),
        "direct_candidates": [direct_center_point],
        "local_homography_candidates": local_homography_candidates,
        "pnp_executed": bool(any(float(value) > 0.0 for value in pnp_times)),
        "pnp_numerical_success": bool(pnp_numerical_success),
        "pnp_physically_valid": bool(pnp_success),
        "pnp_candidate_validations": pnp_validations,
        "inference_uses_ground_truth": False,
    }
    image_center_ground_point = pnp_center_point
    center_point_error = final_center_error
    if pnp_center_point["success"]:
        print(
            "PnP image-center DSM hit: "
            f"({pnp_center_point['x']:.3f}, "
            f"{pnp_center_point['y']:.3f}, "
            f"{pnp_center_point['z']:.3f})"
        )
    else:
        print(f"PnP image-center DSM hit unavailable: {pnp_center_point['reason']}")
    if final_center_error["success"]:
        print(
            f"Final center ({final_center_method}) error: "
            f"{final_center_error['horizontal_error_m']:.3f} m"
        )
    final_confident = bool(use_direct or (pnp_success and final_best_inliers >= args.threshold))
    output_status = (
        "center_localized_high_confidence"
        if final_confident
        else "center_localized_low_confidence"
        if final_center_point.get("success")
        else "center_localization_failed"
    )
    pdm_at_k, recall_at_k, retrieval_gt_rank = _retrieval_metrics_from_ratios(
        pde_list,
        k=retrieval_topn,
        pdm_lambda=opt.pdm_lambda,
        pdm_alpha=opt.pdm_alpha,
    )
    total_wall_time = time.perf_counter() - pipeline_start
    result_pkl = run_dir / f"VG_data_{sample_id}.pkl"
    save_data(
        str(result_pkl),
        opt=opt,
        sample_id=sample_id,
        scene_name=args.scene,
        npz_path=str(selected_path),
        reference_info={key: value for key, value in view.items() if key not in ("map", "dsm")},
        truePos=true_pos,
        pred_loc=pred_loc,
        pred_error=pred_error,
        pnp_success=bool(pnp_success),
        best_index=best_index,
        row_starts=row_starts,
        col_starts=col_starts,
        patch_h=patch_h,
        patch_w=patch_w,
        IR_order=retrieval_order,
        PDE=pde_list,
        inliers=inliers_list,
        XYZ_list=xyz_list,
        location_error_list=location_errors,
        retrieval_time=retrieval_model_time,
        match_time=match_times,
        pnp_time=pnp_times,
        total_time=total_wall_time,
        adaptive_route=decision.route.value,
        image_center_ground_point=image_center_ground_point,
        input_image_center_ground_point=input_image_center_ground_point,
        output_corresponding_point=output_corresponding_point,
        center_correspondence_error=center_point_error,
        match_records=match_records,
        experimental_center_estimation=experimental_center_estimation,
    )

    match_record_paths, match_record_summaries = _save_match_records(run_dir, match_records)

    payload = {
        "method": "CDA-FastReg",
        "execution_mode": "single_process_model_reuse",
        "scene_name": args.scene,
        "sample_id": sample_id,
        "localization": {
            "pnp_success": bool(pnp_success),
            "pnp_numerical_success": bool(pnp_numerical_success),
            "pnp_physically_valid": bool(pnp_success),
            "pnp_physical_failure_reasons": (
                best_validation.get("failure_reasons", []) if best_validation else []
            ),
            "output_status": output_status,
            "final_confident": final_confident,
            "pred_x": _float_or_none(pred_loc.get("x")),
            "pred_y": _float_or_none(pred_loc.get("y")),
            "pred_z": _float_or_none(pred_loc.get("z")),
            "pred_error_m": _float_or_none(pred_error),
            "final_best_inliers": final_best_inliers,
            "raw_best_inliers": raw_best_inliers,
            "best_candidate_rank": int(best_index + 1)
            if pnp_success and best_index is not None
            else None,
        },
        "ground_truth": {"x": true_pos["x"], "y": true_pos["y"], "z": true_pos["z"]},
        "image_center_ground_point": image_center_ground_point,
        "input_image_center_ground_point": input_image_center_ground_point,
        "output_corresponding_point": output_corresponding_point,
        "center_correspondence_error": center_point_error,
        "experimental_center_estimation": experimental_center_estimation,
        "match_record_summaries": match_record_summaries,
        "adaptive_strategy": {
            "route": decision.route.value,
            "top1_best_inliers": top1_best_inliers,
            "confidence_threshold": int(args.threshold),
            "fallback_used": not decision.accepted_top1,
            "fallback_topk": int(args.fallback_topk),
            "fallback_candidates_evaluated": fallback_count,
            "cascade_top5": bool(args.cascade_top5),
            "top2_best_inliers": int(top2_confidence.best_inliers),
            "top5_escalation_used": decision.route.value == "fallback_top5_after_top2",
            "decision_reason": decision.reason,
        },
        "retrieval_metrics": {
            "pdm_at_k": float(pdm_at_k),
            "recall_at_k": float(recall_at_k),
            "retrieval_gt_rank": int(retrieval_gt_rank),
            "retrieval_k": int(retrieval_topn),
            "num_retrieval_candidates": len(row_starts),
        },
        "candidate_inliers": [int(value) for value in inliers_list],
        "timing": {
            "initialization_time_s": initialization_time,
            "reference_prepare_time_s": reference_prepare_time,
            "retrieval_wall_time_s": retrieval_wall_time,
            "top1_match_pnp_wall_time_s": top1_wall_time,
            "fallback_match_pnp_wall_time_s": fallback_wall_time,
            "matching_total_s": retrieval_wall_time + top1_wall_time + fallback_wall_time,
            "online_pipeline_wall_time_s": total_wall_time,
            "model_initializations": 1,
            "retrieval_executions": 1,
        },
        "artifacts": {
            "result_pkl": str(result_pkl),
            "log": str(run_dir / "online_cda.log"),
            "retrieval_dir": str(run_dir / "retrieval"),
            "top1_dir": str(run_dir / "top1"),
            "fallback_dir": str(fallback_dir) if fallback_dir else None,
            "fallback_top5_dir": str(fallback_top5_dir) if fallback_top5_dir else None,
            "match_record_files": match_record_paths,
        },
    }
    retrieval_image = run_dir / "retrieval" / "1_Retrieval.jpg"
    if best_index == 0:
        best_match_candidates = sorted((run_dir / "top1").glob("top1_pnp_inliers_*.jpg"))
    elif fallback_top5_dir is not None:
        best_match_candidates = sorted(fallback_top5_dir.glob("top*.jpg"))
    elif fallback_dir is not None:
        # Fallback-local top1 corresponds to original candidate rank 2.
        best_match_candidates = sorted(fallback_dir.glob(f"top{best_index}_pnp_inliers_*.jpg"))
    else:
        best_match_candidates = []
    best_match_image = best_match_candidates[0] if best_match_candidates else None

    from crossview.visualization.single_result_panel import render_single_result_panel

    panel_path = run_dir / "localization_panel.png"
    position_map_path = run_dir / "position_map.png"
    render_single_result_panel(
        observer_image_bgr=observer_image,
        reference_map_bgr=reference_map_original,
        map_resolution=view["map_resolution"],
        map_origin=view["map_origin_local"],
        payload=payload,
        retrieval_image_path=retrieval_image,
        best_match_image_path=best_match_image,
        output_path=panel_path,
        position_map_path=position_map_path,
    )
    payload["artifacts"]["localization_panel"] = str(panel_path)
    payload["artifacts"]["position_map"] = str(position_map_path)
    payload["artifacts"]["retrieval_image"] = (
        str(retrieval_image) if retrieval_image.exists() else None
    )
    payload["artifacts"]["best_match_image"] = str(best_match_image) if best_match_image else None
    return payload


def main() -> None:
    args = parse_args()
    if args.threshold < 0:
        raise ValueError("--threshold must be non-negative.")
    if not 0 < args.resize_ratio <= 1:
        raise ValueError("--resize-ratio must be in (0, 1].")
    run_tag = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.output_root) / args.scene / Path(args.sample_id).stem / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "online_cda.log"
    with log_path.open("w", encoding="utf-8", buffering=1) as log_file:
        with (
            contextlib.redirect_stdout(TeeStream(sys.stdout, log_file)),
            contextlib.redirect_stderr(TeeStream(sys.stderr, log_file)),
        ):
            payload = _run(args, run_dir)
            if args.dry_run:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                return
            _save_outputs(run_dir, payload)


if __name__ == "__main__":
    main()
