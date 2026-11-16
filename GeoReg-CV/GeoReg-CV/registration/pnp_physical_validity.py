"""Inference-only physical validation for AnyVisLoc PnP poses."""

from __future__ import annotations

import cv2
import numpy as np

from registration.image_center_geolocation import locate_image_center_on_dsm


def _finite_vector(values, size: int) -> np.ndarray | None:
    try:
        array = np.asarray(values, dtype=np.float64).reshape(size)
    except Exception:
        return None
    return array if np.isfinite(array).all() else None


def _reprojection_diagnostics(candidate, match_record, K, dist, image_shape, threshold_px):
    result = {
        "available": False,
        "rmse_px": None,
        "positive_depth_ratio": None,
        "inlier_coverage_ratio": None,
        "approx_inliers": 0,
    }
    if not match_record:
        return result
    image_points = np.asarray(match_record.get("query_points_px", []), dtype=np.float64).reshape(-1, 2)
    world_dataset = np.asarray(match_record.get("world_points_xyz", []), dtype=np.float64).reshape(-1, 3)
    valid = np.isfinite(image_points).all(axis=1) & np.isfinite(world_dataset).all(axis=1)
    image_points = image_points[valid]
    world_dataset = world_dataset[valid]
    if len(image_points) < 4:
        return result

    R = np.asarray(candidate["pose_R_world_to_camera_pnp"], dtype=np.float64).reshape(3, 3)
    t = np.asarray(candidate["pose_t_world_to_camera_pnp"], dtype=np.float64).reshape(3, 1)
    world_pnp = world_dataset.copy()
    world_pnp[:, 1] *= -1.0
    rvec, _ = cv2.Rodrigues(R)
    projected, _ = cv2.projectPoints(
        world_pnp.astype(np.float64),
        rvec,
        t,
        np.asarray(K, dtype=np.float64).reshape(3, 3),
        np.asarray(dist if dist is not None else [], dtype=np.float64).reshape(-1),
    )
    projected = projected.reshape(-1, 2)
    residual = np.linalg.norm(projected - image_points, axis=1)
    approximate_inliers = np.isfinite(residual) & (residual <= float(threshold_px))
    camera_points = (R @ world_pnp.T + t).T
    positive_depth_ratio = float(np.mean(camera_points[:, 2] > 0.0))

    height, width = int(image_shape[0]), int(image_shape[1])
    coverage = 0.0
    rmse = None
    if approximate_inliers.any():
        inlier_points = image_points[approximate_inliers]
        span = np.ptp(inlier_points, axis=0)
        coverage = float((span[0] * span[1]) / max(float(width * height), 1.0))
        rmse = float(np.sqrt(np.mean(np.square(residual[approximate_inliers]))))
    result.update(
        available=True,
        rmse_px=rmse,
        positive_depth_ratio=positive_depth_ratio,
        inlier_coverage_ratio=coverage,
        approx_inliers=int(approximate_inliers.sum()),
    )
    return result


def evaluate_pnp_physical_validity(
    candidate: dict,
    match_record: dict | None,
    K,
    dist,
    image_shape,
    dsm,
    dsm_resolution,
    dsm_origin_local,
    *,
    reprojection_threshold_px: float = 8.0,
    max_inlier_rmse_px: float = 8.0,
    min_positive_depth_ratio: float = 0.80,
    min_inlier_coverage_ratio: float = 0.005,
    min_camera_clearance_m: float = 1.0,
    max_camera_clearance_m: float = 2000.0,
    min_downward_ray_component: float = 0.01,
    max_ray_distance_m: float = 5000.0,
) -> dict:
    """Validate a solved PnP pose without using ground-truth position or pose."""
    checks = {}
    reasons = []
    xyz = _finite_vector(
        [candidate.get("X"), candidate.get("Y"), candidate.get("Z")]
        if candidate else None,
        3,
    )
    R = _finite_vector(candidate.get("pose_R_world_to_camera_pnp") if candidate else None, 9)
    t = _finite_vector(candidate.get("pose_t_world_to_camera_pnp") if candidate else None, 3)
    solved = xyz is not None and R is not None and t is not None
    checks["numerical_solution"] = solved
    if not solved:
        return {
            "pnp_solved": False,
            "physically_valid": False,
            "failure_reasons": ["PnP did not return a finite pose"],
            "checks": checks,
            "center_point": {"success": False, "reason": "PnP pose unavailable"},
        }

    R = R.reshape(3, 3)
    orthogonality_error = float(np.linalg.norm(R.T @ R - np.eye(3), ord="fro"))
    determinant = float(np.linalg.det(R))
    rotation_valid = orthogonality_error <= 0.05 and 0.90 <= determinant <= 1.10
    checks["rotation"] = {
        "passed": rotation_valid,
        "orthogonality_error": orthogonality_error,
        "determinant": determinant,
    }
    if not rotation_valid:
        reasons.append("rotation matrix is invalid")

    res = np.asarray(dsm_resolution, dtype=np.float64).reshape(2)
    origin = np.asarray(dsm_origin_local, dtype=np.float64).reshape(2)
    col = int(round((xyz[0] - origin[0]) / max(abs(res[0]), 1e-12)))
    row = int(round((xyz[1] - origin[1]) / max(abs(res[1]), 1e-12)))
    inside = 0 <= row < dsm.shape[0] and 0 <= col < dsm.shape[1]
    terrain_z = float(dsm[row, col]) if inside else None
    terrain_valid = terrain_z is not None and np.isfinite(terrain_z)
    checks["map_bounds"] = {
        "passed": bool(inside and terrain_valid),
        "row": row,
        "col": col,
        "dsm_height": int(dsm.shape[0]),
        "dsm_width": int(dsm.shape[1]),
        "terrain_z": terrain_z if terrain_valid else None,
    }
    if not inside:
        reasons.append("camera XY is outside the DSM bounds")
    elif not terrain_valid:
        reasons.append("camera XY has no valid DSM elevation")

    clearance = float(xyz[2] - terrain_z) if terrain_valid else None
    clearance_valid = bool(
        clearance is not None
        and float(min_camera_clearance_m) <= clearance <= float(max_camera_clearance_m)
    )
    checks["camera_clearance"] = {
        "passed": clearance_valid,
        "clearance_m": clearance,
        "min_m": float(min_camera_clearance_m),
        "max_m": float(max_camera_clearance_m),
    }
    if terrain_valid and not clearance_valid:
        reasons.append("camera height above terrain is physically implausible")

    reprojection = _reprojection_diagnostics(
        candidate, match_record, K, dist, image_shape, reprojection_threshold_px
    )
    reprojection_valid = bool(
        reprojection["available"]
        and reprojection["rmse_px"] is not None
        and reprojection["rmse_px"] <= float(max_inlier_rmse_px)
        and reprojection["positive_depth_ratio"] >= float(min_positive_depth_ratio)
        and reprojection["inlier_coverage_ratio"] >= float(min_inlier_coverage_ratio)
    )
    checks["reprojection_and_coverage"] = {
        **reprojection,
        "passed": reprojection_valid,
        "max_inlier_rmse_px": float(max_inlier_rmse_px),
        "min_positive_depth_ratio": float(min_positive_depth_ratio),
        "min_inlier_coverage_ratio": float(min_inlier_coverage_ratio),
    }
    if not reprojection_valid:
        reasons.append("reprojection, positive-depth, or inlier-coverage check failed")

    center_point = locate_image_center_on_dsm(
        candidate,
        K,
        dist,
        image_shape,
        dsm,
        dsm_resolution,
        dsm_origin_local,
        max_distance_m=max_ray_distance_m,
    )
    ray = center_point.get("ray_direction_dataset")
    downward_component = -float(ray[2]) if ray is not None and len(ray) == 3 else None
    ray_downward = bool(
        downward_component is not None
        and downward_component >= float(min_downward_ray_component)
    )
    checks["center_ray_direction"] = {
        "passed": ray_downward,
        "downward_component": downward_component,
        "minimum": float(min_downward_ray_component),
    }
    if not ray_downward:
        reasons.append("image-center ray does not point sufficiently downward")
    checks["dsm_intersection"] = {
        "passed": bool(center_point.get("success")),
        "reason": center_point.get("reason"),
        "max_distance_m": float(max_ray_distance_m),
    }
    if not center_point.get("success"):
        reasons.append("image-center ray has no valid DSM intersection")

    physically_valid = bool(
        rotation_valid
        and inside
        and terrain_valid
        and clearance_valid
        and reprojection_valid
        and ray_downward
        and center_point.get("success")
    )
    return {
        "pnp_solved": True,
        "physically_valid": physically_valid,
        "failure_reasons": reasons,
        "checks": checks,
        "center_point": center_point,
    }
