"""Training-free direct image-center geolocation from saved pixel matches."""

from __future__ import annotations

import math

import cv2
import numpy as np


def _empty(reason: str) -> dict:
    return {
        "success": False,
        "reason": reason,
        "method": "direct_local_homography",
        "x": None,
        "y": None,
        "z": None,
        "center_confidence": 0.0,
        "neighborhood_matches": 0,
        "ransac_inliers": 0,
        "inlier_ratio": 0.0,
        "reprojection_error_px": None,
        "mean_roma_confidence": None,
        "high_confidence": False,
    }


def _sample_dsm(dsm, x, y, resolution, origin):
    array = np.asarray(dsm).squeeze()
    res = np.asarray(resolution, dtype=np.float64).reshape(-1)
    org = np.asarray(origin, dtype=np.float64).reshape(-1)
    col = int(round((float(x) - float(org[0])) / max(float(res[0]), 1e-12)))
    row = int(round((float(y) - float(org[1])) / max(float(res[1]), 1e-12)))
    if row < 0 or col < 0 or row >= array.shape[0] or col >= array.shape[1]:
        return None
    value = float(array[row, col])
    return value if math.isfinite(value) else None


def estimate_dense_center(
    match_record: dict,
    *,
    min_center_confidence: float = 0.10,
    max_cycle_error_px: float = 2.0,
) -> dict:
    """Evaluate RoMa's dense query-center correspondence without ground truth.

    The point itself is produced directly by RoMa's dense warp.  Confidence is
    conservative: both forward/backward certainty must be strong and the
    forward-backward cycle must return close to the query-image center.
    """
    dense = match_record.get("dense_center_correspondence") or {}
    result = {
        "success": False,
        "reason": "dense query-center correspondence is unavailable",
        "method": "roma_dense_center",
        "x": None,
        "y": None,
        "z": None,
        "center_confidence": 0.0,
        "forward_certainty": None,
        "backward_certainty": None,
        "cycle_error_px": None,
        "high_confidence": False,
    }
    if not dense.get("success"):
        result["reason"] = dense.get("reason", result["reason"])
        return result

    try:
        x, y, z = float(dense["x"]), float(dense["y"]), float(dense["z"])
        forward = float(dense["forward_certainty"])
        backward = float(dense["backward_certainty"])
        cycle_error = float(dense["cycle_error_px"])
    except (KeyError, TypeError, ValueError):
        result["reason"] = "dense center record contains invalid values"
        return result
    if not all(math.isfinite(v) for v in (x, y, z, forward, backward, cycle_error)):
        result["reason"] = "dense center record contains non-finite values"
        return result

    certainty = float(np.clip(min(forward, backward), 0.0, 1.0))
    cycle_score = math.exp(-cycle_error / max(float(max_cycle_error_px), 1e-6))
    confidence = float(np.clip(certainty * cycle_score, 0.0, 1.0))
    high_confidence = bool(
        confidence >= float(min_center_confidence) and cycle_error <= float(max_cycle_error_px)
    )
    result.update(
        {
            "success": True,
            "reason": "RoMa dense warp evaluated at the query-image center",
            "x": x,
            "y": y,
            "z": z,
            "reference_patch_u": dense.get("reference_patch_u"),
            "reference_patch_v": dense.get("reference_patch_v"),
            "reference_pixel_u": dense.get("reference_map_u"),
            "reference_pixel_v": dense.get("reference_map_v"),
            "forward_certainty": forward,
            "backward_certainty": backward,
            "cycle_error_px": cycle_error,
            "center_confidence": confidence,
            "high_confidence": high_confidence,
            "thresholds": {
                "min_center_confidence": float(min_center_confidence),
                "max_cycle_error_px": float(max_cycle_error_px),
            },
        }
    )
    return result


def estimate_direct_center(
    match_record: dict,
    image_shape,
    dsm,
    dsm_resolution,
    dsm_origin,
    *,
    neighborhood_radius_px: float = 160.0,
    ransac_threshold_px: float = 4.0,
    min_neighborhood_matches: int = 20,
    min_ransac_inliers: int = 12,
    min_inlier_ratio: float = 0.50,
    max_reprojection_error_px: float = 3.0,
    min_center_confidence: float = 0.70,
) -> dict:
    """Map the query-image center into the georeferenced reference map.

    The homography is estimated only from matches near the query center.  All
    confidence decisions depend on match geometry, never on ground truth.
    """
    result = _empty("direct-center estimate was not evaluated")
    query = np.asarray(match_record.get("query_points_px", []), dtype=np.float32).reshape(-1, 2)
    ref = np.asarray(match_record.get("reference_map_points_px", []), dtype=np.float32).reshape(
        -1, 2
    )
    certainty = np.asarray(match_record.get("roma_confidence", []), dtype=np.float32).reshape(-1)
    if len(query) != len(ref) or len(query) < 4:
        result["reason"] = "insufficient saved query/reference matches"
        return result
    if len(certainty) != len(query):
        certainty = np.ones(len(query), dtype=np.float32)

    height, width = int(image_shape[0]), int(image_shape[1])
    center = np.array([(width - 1.0) / 2.0, (height - 1.0) / 2.0], dtype=np.float32)
    finite = np.isfinite(query).all(axis=1) & np.isfinite(ref).all(axis=1) & np.isfinite(certainty)
    distance = np.linalg.norm(query - center[None, :], axis=1)
    selected = finite & (distance <= float(neighborhood_radius_px))
    query_local = query[selected]
    ref_local = ref[selected]
    certainty_local = certainty[selected]
    result["neighborhood_matches"] = int(len(query_local))
    result["mean_roma_confidence"] = (
        float(np.mean(certainty_local)) if len(certainty_local) else None
    )
    if len(query_local) < 4:
        result["reason"] = "fewer than four matches in the center neighborhood"
        return result

    homography, mask = cv2.findHomography(
        query_local,
        ref_local,
        method=cv2.RANSAC,
        ransacReprojThreshold=float(ransac_threshold_px),
        maxIters=10000,
        confidence=0.999,
    )
    if homography is None or mask is None:
        result["reason"] = "local homography estimation failed"
        return result
    inlier_mask = mask.reshape(-1).astype(bool)
    inlier_count = int(inlier_mask.sum())
    inlier_ratio = float(inlier_count / max(len(query_local), 1))
    result["ransac_inliers"] = inlier_count
    result["inlier_ratio"] = inlier_ratio
    if inlier_count < 4:
        result["reason"] = "local homography has fewer than four inliers"
        return result

    projected = cv2.perspectiveTransform(query_local[:, None, :], homography)[:, 0, :]
    residuals = np.linalg.norm(projected - ref_local, axis=1)
    rmse = float(np.sqrt(np.mean(np.square(residuals[inlier_mask]))))
    result["reprojection_error_px"] = rmse
    center_ref = cv2.perspectiveTransform(center.reshape(1, 1, 2), homography)[0, 0]
    if not np.isfinite(center_ref).all():
        result["reason"] = "projected center is not finite"
        return result

    map_res = np.asarray(match_record["map_resolution"], dtype=np.float64).reshape(-1)
    map_origin = np.asarray(match_record["map_origin_local"], dtype=np.float64).reshape(-1)
    x = float(center_ref[0] * map_res[0] + map_origin[0])
    y = float(center_ref[1] * map_res[1] + map_origin[1])
    z = _sample_dsm(dsm, x, y, dsm_resolution, dsm_origin)
    if z is None:
        result["reason"] = "projected center lies outside valid DSM"
        return result

    count_score = min(1.0, inlier_count / max(float(min_ransac_inliers * 2), 1.0))
    ratio_score = min(1.0, inlier_ratio / max(float(min_inlier_ratio), 1e-6))
    error_score = math.exp(-rmse / max(float(max_reprojection_error_px), 1e-6))
    roma_score = float(np.clip(np.mean(certainty_local[inlier_mask]), 0.0, 1.0))
    confidence_score = float(
        np.clip(count_score * ratio_score * error_score * roma_score, 0.0, 1.0)
    )
    high_confidence = bool(
        len(query_local) >= int(min_neighborhood_matches)
        and inlier_count >= int(min_ransac_inliers)
        and inlier_ratio >= float(min_inlier_ratio)
        and rmse <= float(max_reprojection_error_px)
        and confidence_score >= float(min_center_confidence)
    )
    result.update(
        {
            "success": True,
            "reason": "center projected through a local RANSAC homography",
            "x": x,
            "y": y,
            "z": float(z),
            "reference_pixel_u": float(center_ref[0]),
            "reference_pixel_v": float(center_ref[1]),
            "center_confidence": confidence_score,
            "high_confidence": high_confidence,
            "neighborhood_radius_px": float(neighborhood_radius_px),
            "thresholds": {
                "min_neighborhood_matches": int(min_neighborhood_matches),
                "min_ransac_inliers": int(min_ransac_inliers),
                "min_inlier_ratio": float(min_inlier_ratio),
                "max_reprojection_error_px": float(max_reprojection_error_px),
                "min_center_confidence": float(min_center_confidence),
            },
        }
    )
    return result


def point_distance(a: dict, b: dict) -> float | None:
    if not a.get("success") or not b.get("success"):
        return None
    return float(math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"])))
