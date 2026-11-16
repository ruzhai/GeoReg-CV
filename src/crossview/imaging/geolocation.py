"""Geolocate the image-center ray by intersecting it with an AnyVisLoc DSM."""

from __future__ import annotations

import cv2
import numpy as np


def _sample_dsm(dsm, x, y, resolution, origin):
    res = np.asarray(resolution, dtype=np.float64).reshape(2)
    org = np.asarray(origin, dtype=np.float64).reshape(2)
    col = int(round((float(x) - org[0]) / max(res[0], 1e-12)))
    row = int(round((float(y) - org[1]) / max(res[1], 1e-12)))
    if row < 0 or col < 0 or row >= dsm.shape[0] or col >= dsm.shape[1]:
        return None
    z = float(dsm[row, col])
    return z if np.isfinite(z) else None


def _intersect_dataset_ray(camera, ray_dataset, u, v, dsm, resolution, origin, max_distance_m):
    base = {"success": False, "source": "aerial_dsm"}
    ray_dataset = np.asarray(ray_dataset, dtype=np.float64).reshape(3)
    norm = float(np.linalg.norm(ray_dataset))
    if not np.isfinite(norm) or norm < 1e-12:
        return {**base, "reason": "invalid image-center ray"}
    ray_dataset /= norm
    camera = np.asarray(camera, dtype=np.float64).reshape(3)
    res = np.asarray(resolution, dtype=np.float64).reshape(2)
    step = max(0.5, min(abs(float(res[0])), abs(float(res[1]))))
    distances = np.arange(0.0, float(max_distance_m) + step, step)
    points = camera[None, :] + distances[:, None] * ray_dataset[None, :]
    previous = None
    bracket = None
    for distance, point in zip(distances, points, strict=False):
        terrain_z = _sample_dsm(dsm, point[0], point[1], res, origin)
        if terrain_z is None:
            previous = None
            continue
        clearance = float(point[2] - terrain_z)
        if previous is not None and previous[1] > 0.0 and clearance <= 0.0:
            bracket = (previous[0], float(distance))
            break
        previous = (float(distance), clearance)
    if bracket is None:
        return {
            **base,
            "reason": "image-center ray did not intersect valid DSM within range",
            "center_pixel_u": float(u),
            "center_pixel_v": float(v),
            "max_distance_m": float(max_distance_m),
            "ray_direction_dataset": ray_dataset.tolist(),
        }
    low, high = bracket
    for _ in range(24):
        mid = 0.5 * (low + high)
        point = camera + mid * ray_dataset
        terrain_z = _sample_dsm(dsm, point[0], point[1], res, origin)
        if terrain_z is None or point[2] - terrain_z > 0.0:
            low = mid
        else:
            high = mid
    distance = high
    point = camera + distance * ray_dataset
    terrain_z = _sample_dsm(dsm, point[0], point[1], res, origin)
    if terrain_z is not None:
        point[2] = terrain_z
    return {
        "success": True,
        "reason": "image-center ray intersected aerial DSM",
        "source": "aerial_dsm",
        "center_pixel_u": float(u),
        "center_pixel_v": float(v),
        "x": float(point[0]),
        "y": float(point[1]),
        "z": float(point[2]),
        "slant_distance_from_camera_m": float(distance),
        "horizontal_distance_from_camera_m": float(np.linalg.norm(point[:2] - camera[:2])),
        "ray_direction_dataset": ray_dataset.tolist(),
    }


def locate_image_center_on_dsm(
    candidate: dict,
    K,
    dist,
    image_shape,
    dsm,
    dsm_resolution,
    dsm_origin_local,
    max_distance_m: float = 5000.0,
) -> dict:
    """Return the dataset-local XYZ hit of the center pixel's viewing ray.

    PnP uses [X, -Y, Z] as its world frame. The returned point is converted
    back to AnyVisLoc's dataset-local [X, Y, Z] convention.
    """
    base = {"success": False, "source": "aerial_dsm"}
    if not candidate or candidate.get("X") is None:
        return {**base, "reason": "best PnP candidate has no valid camera position"}
    R_value = candidate.get("pose_R_world_to_camera_pnp")
    if R_value is None:
        return {**base, "reason": "PnP rotation was not retained"}

    height, width = int(image_shape[0]), int(image_shape[1])
    u, v = (width - 1.0) * 0.5, (height - 1.0) * 0.5
    K = np.asarray(K, dtype=np.float64).reshape(3, 3)
    dist = np.asarray(dist if dist is not None else [], dtype=np.float64).reshape(-1)
    pixel = np.array([[[u, v]]], dtype=np.float64)
    normalized = cv2.undistortPoints(pixel, K, dist if dist.size else None).reshape(2)
    ray_camera = np.array([normalized[0], normalized[1], 1.0], dtype=np.float64)

    R = np.asarray(R_value, dtype=np.float64).reshape(3, 3)
    ray_pnp = R.T @ ray_camera
    ray_dataset = np.array([ray_pnp[0], -ray_pnp[1], ray_pnp[2]], dtype=np.float64)
    camera = np.array([candidate["X"], candidate["Y"], candidate["Z"]], dtype=np.float64)
    return _intersect_dataset_ray(
        camera, ray_dataset, u, v, dsm, dsm_resolution, dsm_origin_local, max_distance_m
    )


def locate_ground_truth_image_center_on_dsm(
    pose_c2w,
    camera_xyz,
    K,
    dist,
    image_shape,
    dsm,
    dsm_resolution,
    dsm_origin_local,
    max_distance_m: float = 5000.0,
) -> dict:
    """Intersect the input center ray from the AnyVisLoc ground-truth pose."""
    height, width = int(image_shape[0]), int(image_shape[1])
    u, v = (width - 1.0) * 0.5, (height - 1.0) * 0.5
    K = np.asarray(K, dtype=np.float64).reshape(3, 3)
    dist = np.asarray(dist if dist is not None else [], dtype=np.float64).reshape(-1)
    normalized = cv2.undistortPoints(
        np.array([[[u, v]]], dtype=np.float64), K, dist if dist.size else None
    ).reshape(2)
    # AnyVisLoc pose_c2w follows an OpenGL-like camera convention (forward=-Z,
    # image up=+Y). Its stored rotation uses an XY frame rotated 90 degrees
    # relative to the dataset-local map axes: dataset direction = [-world_y,
    # world_x, world_z]. Translation/xyz is already stored in dataset-local XYZ.
    ray_camera = np.array([normalized[0], -normalized[1], -1.0], dtype=np.float64)
    rotation_c2w = np.asarray(pose_c2w, dtype=np.float64).reshape(4, 4)[:3, :3]
    ray_world = rotation_c2w @ ray_camera
    ray_dataset = np.array([-ray_world[1], ray_world[0], ray_world[2]], dtype=np.float64)
    result = _intersect_dataset_ray(
        camera_xyz, ray_dataset, u, v, dsm, dsm_resolution, dsm_origin_local, max_distance_m
    )
    result["definition"] = "ground-truth input-image center DSM hit"
    return result


def center_correspondence_error(input_center: dict, output_point: dict) -> dict:
    if not input_center.get("success") or not output_point.get("success"):
        return {"success": False, "reason": "one or both center points are unavailable"}
    dx = float(output_point["x"]) - float(input_center["x"])
    dy = float(output_point["y"]) - float(input_center["y"])
    dz = float(output_point["z"]) - float(input_center["z"])
    return {
        "success": True,
        "horizontal_error_m": float(np.hypot(dx, dy)),
        "three_dimensional_error_m": float(np.sqrt(dx * dx + dy * dy + dz * dz)),
        "dx_m": dx,
        "dy_m": dy,
        "dz_m": dz,
    }
