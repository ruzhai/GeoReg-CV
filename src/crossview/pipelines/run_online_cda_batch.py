"""Single-process batch runner for the online CDA-FastReg cascade."""

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from crossview.pipelines.run_online_cda_sample import TeeStream, _run, _save_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run online CDA-FastReg for many samples in one Python process."
    )
    parser.add_argument("--scene", required=True)
    parser.add_argument("--config", default="D:/GeoReg-CV/configs/anyvisloc_baseline.yaml")
    parser.add_argument("--output-root", default="D:/GeoReg-CV/outputs/online_cda_batch")
    parser.add_argument(
        "--limit", type=int, default=120, help="Number of sorted samples; 0 means all."
    )
    parser.add_argument("--threshold", type=int, default=1000)
    parser.add_argument("--fallback-topk", type=int, choices=[2, 5], default=2)
    cascade = parser.add_mutually_exclusive_group()
    cascade.add_argument("--cascade-top5", dest="cascade_top5", action="store_true")
    cascade.add_argument("--no-cascade-top5", dest="cascade_top5", action="store_false")
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
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Save per-sample visualizations; slower and larger.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit < 0:
        raise ValueError("--limit must be non-negative")
    if args.threshold < 0:
        raise ValueError("--threshold must be non-negative")
    if not 0 < args.resize_ratio <= 1:
        raise ValueError("--resize-ratio must be in (0, 1]")

    import yaml

    with Path(args.config).open("r", encoding="utf-8") as f:
        wrapper = yaml.safe_load(f)
    dataset_root = Path(wrapper["anyvisloc"]["dataset_root"])
    scene_root = dataset_root / args.scene
    samples = sorted(scene_root.glob("*.npz"), key=lambda p: p.name)
    if args.limit:
        samples = samples[: args.limit]
    if not samples:
        raise FileNotFoundError(f"No NPZ samples found under {scene_root}")

    batch_tag = datetime.now().strftime("%Y%m%d-%H%M%S")
    batch_root = Path(args.output_root) / args.scene / batch_tag
    batch_root.mkdir(parents=True, exist_ok=True)
    log_path = batch_root / "batch.log"
    records = []
    failures = []
    batch_start = time.perf_counter()

    with log_path.open("w", encoding="utf-8", buffering=1) as log_file:
        stream = TeeStream(sys.stdout, log_file)
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            print(f"Single-process batch start: {args.scene}, samples={len(samples)}")
            print(f"Batch output: {batch_root}")
            for index, sample_path in enumerate(samples, start=1):
                sample_id = sample_path.stem
                run_dir = batch_root / sample_id
                run_dir.mkdir(parents=True, exist_ok=True)
                sample_args = argparse.Namespace(
                    sample_id=sample_id,
                    scene=args.scene,
                    config=args.config,
                    output_root=str(args.output_root),
                    threshold=args.threshold,
                    fallback_topk=args.fallback_topk,
                    cascade_top5=args.cascade_top5,
                    match_keypoints=args.match_keypoints,
                    resize_ratio=args.resize_ratio,
                    patch_scale=args.patch_scale,
                    direct_center=args.direct_center,
                    center_radius=args.center_radius,
                    center_confidence_threshold=args.center_confidence_threshold,
                    center_cycle_threshold_px=args.center_cycle_threshold_px,
                    pnp_min_clearance_m=args.pnp_min_clearance_m,
                    pnp_max_clearance_m=args.pnp_max_clearance_m,
                    pnp_min_inlier_coverage=args.pnp_min_inlier_coverage,
                    center_execution_mode=args.center_execution_mode,
                    visualize=args.visualize,
                    dry_run=False,
                )
                sample_start = time.perf_counter()
                print(f"[{index}/{len(samples)}] {args.scene}/{sample_id}")
                try:
                    payload = _run(sample_args, run_dir)
                    payload["artifacts"]["log"] = str(log_path)
                    _save_outputs(run_dir, payload)
                    records.append(payload)
                    route = payload["adaptive_strategy"]["route"]
                    center_error = payload.get("experimental_center_estimation", {}).get(
                        "center_error_m"
                    )
                    error_text = (
                        f"{center_error:.3f} m" if center_error is not None else "unavailable"
                    )
                    print(
                        f"Completed {sample_id}: center_error={error_text}, route={route}, elapsed={time.perf_counter() - sample_start:.2f} s"
                    )
                except Exception as exc:
                    failures.append({"sample_id": sample_id, "error": repr(exc)})
                    print(f"FAILED {sample_id}: {exc}")

            total_time = time.perf_counter() - batch_start
            summary = summarize(records, failures, total_time, batch_root, log_path)
            (batch_root / "batch_summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            write_summary_csv(batch_root / "batch_records.csv", records)
            (batch_root / "batch_failures.json").write_text(
                json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"Batch complete: {len(records)}/{len(samples)} succeeded")
            print(f"Total elapsed: {total_time:.2f} s")
            print(f"Summary: {batch_root / 'batch_summary.json'}")


def summarize(records, failures, total_time, batch_root, log_path):
    errors = [
        r.get("experimental_center_estimation", {}).get("center_error_m")
        for r in records
        if r.get("experimental_center_estimation", {}).get("center_error_m") is not None
    ]
    routes = {}
    center_methods = {}
    for record in records:
        route = record["adaptive_strategy"]["route"]
        routes[route] = routes.get(route, 0) + 1
        center_method = record.get("experimental_center_estimation", {}).get(
            "center_method", "unknown"
        )
        center_methods[center_method] = center_methods.get(center_method, 0) + 1
    return {
        "execution_mode": "single_process_batch_model_reuse",
        "samples_completed": len(records),
        "samples_failed": len(failures),
        "mean_error_m": sum(errors) / len(errors) if errors else None,
        "success_1m_pct": sum(e <= 1 for e in errors) / len(errors) * 100 if errors else None,
        "success_3m_pct": sum(e <= 3 for e in errors) / len(errors) * 100 if errors else None,
        "success_5m_pct": sum(e <= 5 for e in errors) / len(errors) * 100 if errors else None,
        "route_counts": routes,
        "center_method_counts": center_methods,
        "total_wall_time_s": total_time,
        "mean_wall_time_per_completed_sample_s": total_time / len(records) if records else None,
        "output_root": str(batch_root),
        "batch_log": str(log_path),
    }


def write_summary_csv(path: Path, records) -> None:
    rows = []
    for record in records:
        rows.append(
            {
                "scene_name": record["scene_name"],
                "sample_id": record["sample_id"],
                "pred_error_m": record["localization"]["pred_error_m"],
                "final_best_inliers": record["localization"]["final_best_inliers"],
                "raw_best_inliers": record["localization"].get("raw_best_inliers"),
                "pnp_numerical_success": record["localization"].get("pnp_numerical_success"),
                "pnp_physically_valid": record["localization"].get("pnp_physically_valid"),
                "route": record["adaptive_strategy"]["route"],
                "top1_best_inliers": record["adaptive_strategy"]["top1_best_inliers"],
                "top2_best_inliers": record["adaptive_strategy"].get("top2_best_inliers"),
                "top5_escalation_used": record["adaptive_strategy"].get("top5_escalation_used"),
                "total_time_s": record["timing"]["online_pipeline_wall_time_s"],
                "initialization_time_s": record["timing"]["initialization_time_s"],
                "center_ground_success": record.get("image_center_ground_point", {}).get("success"),
                "center_ground_x": record.get("image_center_ground_point", {}).get("x"),
                "center_ground_y": record.get("image_center_ground_point", {}).get("y"),
                "center_ground_z": record.get("image_center_ground_point", {}).get("z"),
                "input_center_gt_x": record.get("input_image_center_ground_point", {}).get("x"),
                "input_center_gt_y": record.get("input_image_center_ground_point", {}).get("y"),
                "input_center_gt_z": record.get("input_image_center_ground_point", {}).get("z"),
                "output_corresponding_x": record.get("output_corresponding_point", {}).get("x"),
                "output_corresponding_y": record.get("output_corresponding_point", {}).get("y"),
                "output_corresponding_z": record.get("output_corresponding_point", {}).get("z"),
                "center_correspondence_error_m": record.get("center_correspondence_error", {}).get(
                    "horizontal_error_m"
                ),
                "center_method": record.get("experimental_center_estimation", {}).get(
                    "center_method"
                ),
                "center_confidence": record.get("experimental_center_estimation", {}).get(
                    "center_confidence"
                ),
                "center_cycle_error_px": record.get("experimental_center_estimation", {})
                .get("direct_center_point", {})
                .get("cycle_error_px"),
                "center_forward_certainty": record.get("experimental_center_estimation", {})
                .get("direct_center_point", {})
                .get("forward_certainty"),
                "center_backward_certainty": record.get("experimental_center_estimation", {})
                .get("direct_center_point", {})
                .get("backward_certainty"),
                "pnp_executed": record.get("experimental_center_estimation", {}).get(
                    "pnp_executed"
                ),
                "direct_center_error_m": record.get("experimental_center_estimation", {}).get(
                    "direct_center_error_m"
                ),
                "pnp_center_error_m": record.get("experimental_center_estimation", {}).get(
                    "pnp_center_error_m"
                ),
                "hybrid_center_error_m": record.get("experimental_center_estimation", {}).get(
                    "center_error_m"
                ),
                "direct_vs_pnp_distance_m": record.get("experimental_center_estimation", {}).get(
                    "direct_vs_pnp_distance_m"
                ),
                "matching_total_s": record.get("timing", {}).get("matching_total_s"),
            }
        )
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
