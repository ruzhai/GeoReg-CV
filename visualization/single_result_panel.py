"""Render single-sample GeoReg-CV localization outputs."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    for candidate in (
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _bgr_to_pil(image_bgr: np.ndarray) -> Image.Image:
    rgb = cv2.cvtColor(np.asarray(image_bgr), cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def _fit(image: Image.Image, size: tuple[int, int], background=(9, 15, 28)):
    image = image.convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, background)
    offset = ((size[0] - image.width) // 2, (size[1] - image.height) // 2)
    canvas.paste(image, offset)
    return canvas, offset, (image.width, image.height)


def _load_optional(path: str | Path | None, size: tuple[int, int], label: str):
    if path and Path(path).exists():
        with Image.open(path) as image:
            return _fit(image.copy(), size)[0]
    canvas = Image.new("RGB", size, (9, 15, 28))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, size[1] // 2 - 12), label, font=_font(20), fill=(148, 163, 184))
    return canvas


def _position_map(
    reference_map_bgr: np.ndarray,
    map_resolution,
    map_origin,
    input_center,
    output_corresponding,
    size=(1000, 570),
):
    original_h, original_w = reference_map_bgr.shape[:2]
    fitted = _bgr_to_pil(reference_map_bgr).convert("RGB")
    fitted.thumbnail(size, Image.Resampling.LANCZOS)
    fitted_size = (fitted.width, fitted.height)
    centered_x = (size[0] - fitted.width) // 2
    # Reserve a wider column for the legend and move the tall reference map
    # rightwards. This prevents the long label from crossing its border.
    reserved_left = 350
    offset = (
        min(max(centered_x, reserved_left), size[0] - fitted.width),
        (size[1] - fitted.height) // 2,
    )
    overview = Image.new("RGB", size, (9, 15, 28))
    overview.paste(fitted, offset)
    draw = ImageDraw.Draw(overview)
    res_x, res_y = float(map_resolution[0]), float(map_resolution[1])
    origin_x, origin_y = float(map_origin[0]), float(map_origin[1])

    def project(x, y):
        col = (float(x) - origin_x) / max(res_x, 1e-12)
        row = (float(y) - origin_y) / max(res_y, 1e-12)
        raw_x = offset[0] + col / original_w * fitted_size[0]
        raw_y = offset[1] + row / original_h * fitted_size[1]
        min_x, max_x = offset[0], offset[0] + fitted_size[0]
        min_y, max_y = offset[1], offset[1] + fitted_size[1]
        clipped = not (min_x <= raw_x <= max_x and min_y <= raw_y <= max_y)
        return (
            min(max(raw_x, min_x), max_x),
            min(max(raw_y, min_y), max_y),
            clipped,
        )

    font = _font(18)
    clipped = False
    if input_center.get("success") and output_corresponding.get("success"):
        gx, gy, gt_clipped = project(input_center["x"], input_center["y"])
        px, py, pred_clipped = project(output_corresponding["x"], output_corresponding["y"])
        clipped = gt_clipped or pred_clipped
        draw.line((gx, gy, px, py), fill=(248, 113, 113), width=5)
        draw.ellipse((gx - 9, gy - 9, gx + 9, gy + 9), fill=(34, 197, 94), outline="white", width=2)
        draw.ellipse((px - 9, py - 9, px + 9, py + 9), fill=(14, 165, 233), outline="white", width=2)
    legend_items = [
        ((34, 197, 94), "Input center GT"),
        ((14, 165, 233), "Output corresponding point"),
    ]
    legend_h = 14 + 27 * len(legend_items)
    draw.rounded_rectangle((14, 14, 320, 14 + legend_h), radius=7, fill=(2, 6, 23), outline=(71, 85, 105), width=1)
    for item_index, (color, text) in enumerate(legend_items):
        item_y = 27 + item_index * 27
        draw.ellipse((27, item_y, 41, item_y + 14), fill=color, outline="white", width=1)
        draw.text((50, item_y - 4), text, font=font, fill=(226, 232, 240))
    if clipped:
        draw.text((18, size[1] - 34), "A center correspondence point is outside the map boundary.", font=font, fill=(254, 202, 202))
    return overview


def render_single_result_panel(
    *,
    observer_image_bgr: np.ndarray,
    reference_map_bgr: np.ndarray,
    map_resolution,
    map_origin,
    payload: dict,
    retrieval_image_path: str | Path | None,
    best_match_image_path: str | Path | None,
    output_path: str | Path,
    position_map_path: str | Path,
) -> None:
    output_path = Path(output_path)
    position_map_path = Path(position_map_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    loc = payload["localization"]
    strategy = payload["adaptive_strategy"]
    timing = payload["timing"]
    gt = payload["ground_truth"]
    input_center = payload.get("input_image_center_ground_point", {})
    output_point = payload.get("output_corresponding_point", {})
    center_error = payload.get("center_correspondence_error", {})
    position = _position_map(
        reference_map_bgr,
        map_resolution,
        map_origin,
        payload.get("input_image_center_ground_point", {}),
        payload.get("output_corresponding_point", {}),
    )
    position.save(position_map_path)

    observer = _fit(_bgr_to_pil(observer_image_bgr), (520, 330))[0]
    # The summary panel intentionally omits the PnP inlier image.  The raw
    # match artifact is still generated separately when visualization is
    # enabled, but it is too dense for the overview requested by the user.
    retrieval = _load_optional(retrieval_image_path, (1220, 330), "Retrieval image unavailable. Enable visualization.")

    canvas = Image.new("RGB", (1800, 1080), (2, 6, 23))
    draw = ImageDraw.Draw(canvas)
    title_font = _font(31)
    label_font = _font(20)
    section_font = _font(24)
    info_font = _font(22)
    status_color = (34, 197, 94) if loc["final_confident"] else (250, 204, 21)
    center_error_text = (
        f"Center error {center_error['horizontal_error_m']:.3f} m"
        if center_error.get("success")
        else "Center correspondence unavailable"
    )
    title = (
        f"GeoReg-CV | {payload['scene_name']}/{payload['sample_id']} | "
        f"{loc['output_status']} | {center_error_text}"
    )
    draw.text((30, 20), title, font=title_font, fill=status_color)

    boxes = [
        ((30, 100), observer, "Observer / oblique query"),
        ((560, 100), retrieval, "Aerial retrieval candidates"),
    ]
    for origin, image, label in boxes:
        draw.text((origin[0], origin[1] - 30), label, font=label_font, fill=(226, 232, 240))
        canvas.paste(image, origin)
        draw.rectangle((origin[0], origin[1], origin[0] + image.width, origin[1] + image.height), outline=(51, 65, 85), width=2)

    canvas.paste(position, (30, 485))
    draw.text((30, 452), "Aerial reference map: input-center GT and output corresponding point", font=label_font, fill=(226, 232, 240))

    info_x, info_y = 1060, 485
    draw.rounded_rectangle((info_x, info_y, 1770, 1035), radius=8, fill=(15, 23, 42), outline=(51, 65, 85), width=2)
    metrics = payload["retrieval_metrics"]
    experiment = payload.get("experimental_center_estimation", {})
    matching_total = (
        timing["retrieval_wall_time_s"]
        + timing["top1_match_pnp_wall_time_s"]
        + timing["fallback_match_pnp_wall_time_s"]
    )
    if loc.get("pred_error_m") is not None:
        camera_status_line = f"Camera localization error: {loc['pred_error_m']:.3f} m"
    elif loc.get("pnp_numerical_success") and not loc.get("pnp_physically_valid"):
        camera_status_line = "PnP: solved numerically, rejected physically"
    else:
        camera_status_line = "PnP: not solved or not executed"
    if loc.get("best_candidate_rank") is not None:
        pnp_rank_line = (
            f"Best rank: {loc['best_candidate_rank']} | Valid inliers: "
            f"{loc['final_best_inliers']}"
        )
    elif loc.get("pnp_numerical_success"):
        pnp_rank_line = (
            f"Physical valid: no | Raw best inliers: {loc.get('raw_best_inliers', 0)}"
        )
    else:
        pnp_rank_line = "Best rank / inliers: N/A"
    lines = [
        "Center correspondence",
        (
            f"Input GT: ({input_center['x']:.3f}, {input_center['y']:.3f}, {input_center['z']:.3f})"
            if input_center.get("success") else "Input GT: unavailable"
        ),
        (
            f"Output: ({output_point['x']:.3f}, {output_point['y']:.3f}, {output_point['z']:.3f})"
            if output_point.get("success") else "Output: unavailable"
        ),
        (
            f"Horizontal error: {center_error['horizontal_error_m']:.3f} m"
            if center_error.get("success") else "Horizontal error: unavailable"
        ),
        "",
        "Camera / PnP diagnostics",
        camera_status_line,
        pnp_rank_line,
        "",
        "Adaptive strategy",
        f"Route: {strategy['route']}",
        f"Top1 inliers: {strategy['top1_best_inliers']} | Threshold: {strategy['confidence_threshold']}",
        f"Fallback: {strategy['fallback_used']} | Candidates: {len(payload['candidate_inliers'])}",
        f"Center method: {experiment.get('center_method', 'N/A')}",
        f"Center confidence: {experiment.get('center_confidence', 0.0):.3f}",
        "",
        "Retrieval and timing",
        f"Retrieval GT rank: {metrics['retrieval_gt_rank']}",
        f"Retrieval: {timing['retrieval_wall_time_s']:.2f} s",
        f"Top1 match + PnP: {timing['top1_match_pnp_wall_time_s']:.2f} s",
        f"Fallback match + PnP: {timing['fallback_match_pnp_wall_time_s']:.2f} s",
        f"Matching total: {matching_total:.2f} s",
        f"Total: {timing['online_pipeline_wall_time_s']:.2f} s",
    ]
    header_indices = (0, 5, 9, 16)
    y = info_y + 22
    for index, line in enumerate(lines):
        if not line:
            y += 11
            continue
        color = status_color if index in header_indices else (226, 232, 240)
        draw.text((info_x + 24, y), line, font=section_font if index in header_indices else info_font, fill=color)
        y += 31 if index in header_indices else 24

    canvas.save(output_path)
