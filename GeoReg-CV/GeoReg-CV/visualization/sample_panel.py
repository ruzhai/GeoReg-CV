import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _float(value, default=0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def _load_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _get(row: Dict[str, str], *keys, default=""):
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return default


def _read_observer_image(npz_path: Path, size: Tuple[int, int]) -> Image.Image:
    data = np.load(npz_path, allow_pickle=True)
    image = data["image"]
    img = Image.fromarray(image.astype(np.uint8), mode="RGB")
    img.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (15, 23, 42))
    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def _read_reference_map(scene_dir: Path, size: Tuple[int, int]) -> Image.Image:
    map_path = scene_dir / "aerial_map.png"
    try:
        import cv2

        arr = cv2.imread(str(map_path), cv2.IMREAD_REDUCED_COLOR_8)
        if arr is None:
            raise RuntimeError("cv2.imread returned None")
        arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(arr)
    except Exception:
        Image.MAX_IMAGE_PIXELS = None
        img = Image.open(map_path).convert("RGB")

    img.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (15, 23, 42))
    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def _font(size=22):
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for c in candidates:
        p = Path(c)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _draw_label(draw: ImageDraw.ImageDraw, xy, text, font, fill=(229, 231, 235)):
    draw.text(xy, text, fill=fill, font=font)


def _coord_bounds(rows: Iterable[Dict[str, str]]):
    xs = [_float(r["gt_x"]) for r in rows]
    ys = [_float(r["gt_y"]) for r in rows]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    pad_x = (max_x - min_x) * 0.06 or 1
    pad_y = (max_y - min_y) * 0.06 or 1
    return min_x - pad_x, max_x + pad_x, min_y - pad_y, max_y + pad_y


def _world_to_panel(x, y, bounds, panel_origin, panel_size):
    min_x, max_x, min_y, max_y = bounds
    ox, oy = panel_origin
    w, h = panel_size
    px = ox + (x - min_x) / (max_x - min_x) * w
    py = oy + h - (y - min_y) / (max_y - min_y) * h
    clipped = False
    if px < ox:
        px = ox
        clipped = True
    if px > ox + w:
        px = ox + w
        clipped = True
    if py < oy:
        py = oy
        clipped = True
    if py > oy + h:
        py = oy + h
        clipped = True
    return px, py, clipped


def render_sample_panel(
    row: Dict[str, str],
    all_rows: List[Dict[str, str]],
    dataset_root: str | Path,
    output_path: str | Path,
) -> None:
    dataset_root = Path(dataset_root)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scene_name = row["scene_name"]
    sample_id = row["sample_id"]
    scene_dir = dataset_root / scene_name
    npz_path = Path(_get(row, "npz_path", "observer_source"))

    W, H = 1800, 920
    margin = 30
    observer_box = (540, 560)
    ref_box = (700, 560)
    info_box = (440, 560)

    canvas = Image.new("RGB", (W, H), (2, 6, 23))
    draw = ImageDraw.Draw(canvas)
    title_font = _font(32)
    normal_font = _font(22)
    small_font = _font(18)

    error = _float(_get(row, "pred_error_m", "error_m"))
    status = "成功样本" if error <= 1 else ("边界样本" if error <= 5 else "失败样本")
    status_color = (34, 197, 94) if error <= 1 else ((250, 204, 21) if error <= 5 else (239, 68, 68))

    _draw_label(
        draw,
        (margin, 22),
        f"GeoReg-CV 可视化：{scene_name}/{sample_id}  |  {status}  |  Error={error:.2f}m",
        title_font,
        status_color,
    )

    observer_img = _read_observer_image(npz_path, observer_box)
    ref_img = _read_reference_map(scene_dir, ref_box)

    obs_origin = (margin, 105)
    ref_origin = (margin + observer_box[0] + 30, 105)
    info_origin = (margin + observer_box[0] + ref_box[0] + 60, 105)

    canvas.paste(observer_img, obs_origin)
    canvas.paste(ref_img, ref_origin)
    draw.rectangle([obs_origin, (obs_origin[0] + observer_box[0], obs_origin[1] + observer_box[1])], outline=(51, 65, 85), width=2)
    draw.rectangle([ref_origin, (ref_origin[0] + ref_box[0], ref_origin[1] + ref_box[1])], outline=(51, 65, 85), width=2)

    _draw_label(draw, (obs_origin[0], obs_origin[1] - 32), "观察者视角图像（AnyVisLoc oblique query）", normal_font)
    _draw_label(draw, (ref_origin[0], ref_origin[1] - 32), "无人机/航拍参考视图（aerial reference）", normal_font)

    bounds = _coord_bounds([r for r in all_rows if r["scene_name"] == scene_name])
    gx, gy, _ = _world_to_panel(_float(row["gt_x"]), _float(row["gt_y"]), bounds, ref_origin, ref_box)
    px, py, clipped = _world_to_panel(_float(row["pred_x"]), _float(row["pred_y"]), bounds, ref_origin, ref_box)

    draw.line([(gx, gy), (px, py)], fill=(248, 113, 113), width=4)
    draw.ellipse([gx - 8, gy - 8, gx + 8, gy + 8], fill=(34, 197, 94), outline=(240, 253, 244), width=2)
    draw.ellipse([px - 8, py - 8, px + 8, py + 8], fill=(249, 115, 22), outline=(255, 247, 237), width=2)
    _draw_label(draw, (gx + 12, gy - 12), "GT", small_font, (187, 247, 208))
    _draw_label(draw, (px + 12, py + 8), "Pred", small_font, (254, 215, 170))
    if clipped:
        _draw_label(draw, (ref_origin[0] + 12, ref_origin[1] + ref_box[1] - 30), "注：估计点超出当前场景坐标边界，已贴边显示", small_font, (254, 202, 202))

    legend_y = ref_origin[1] + ref_box[1] + 18
    draw.ellipse([ref_origin[0], legend_y, ref_origin[0] + 16, legend_y + 16], fill=(34, 197, 94))
    _draw_label(draw, (ref_origin[0] + 25, legend_y - 3), "真实位置", small_font)
    draw.ellipse([ref_origin[0] + 130, legend_y, ref_origin[0] + 146, legend_y + 16], fill=(249, 115, 22))
    _draw_label(draw, (ref_origin[0] + 155, legend_y - 3), "估计位置", small_font)
    draw.line([(ref_origin[0] + 280, legend_y + 8), (ref_origin[0] + 340, legend_y + 8)], fill=(248, 113, 113), width=3)
    _draw_label(draw, (ref_origin[0] + 350, legend_y - 3), "定位误差连线", small_font)

    info_lines = [
        "系统输出信息",
        f"Scene: {scene_name}",
        f"Sample: {sample_id}",
        "",
        f"GT:   ({_float(row['gt_x']):.2f}, {_float(row['gt_y']):.2f}, {_float(row['gt_z']):.2f})",
        f"Pred: ({_float(row['pred_x']):.2f}, {_float(row['pred_y']):.2f}, {_float(row['pred_z']):.2f})",
        f"Error: {error:.2f} m",
        "",
        f"Retrieval: {row.get('retrieval_method', '')}",
        f"Matching: {row.get('matching_method', '')}",
        f"Localization: {_get(row, 'localization_method', default='PnP/P3P')}",
        f"GT Rank: {row.get('retrieval_gt_rank', '')}",
        f"Recall@K: {row.get('recall_at_k', '')}",
        f"PDM@K: {_float(row.get('pdm_at_k')):.4f}",
        f"Best Inliers: {_get(row, 'best_inliers')}",
        f"Total Time: {_float(_get(row, 'total_time', 'total_time_s')):.2f} s",
    ]
    if _get(row, "adaptive_route"):
        info_lines.extend(
            [
                "",
                f"CDA Route: {_get(row, 'adaptive_route')}",
                f"Top1 Inliers: {_get(row, 'top1_best_inliers')}",
                f"Threshold: {_get(row, 'confidence_threshold')}",
                f"Fallback: {_get(row, 'fallback_used')}",
            ]
        )

    draw.rounded_rectangle(
        [info_origin, (info_origin[0] + info_box[0], info_origin[1] + info_box[1])],
        radius=18,
        fill=(15, 23, 42),
        outline=(51, 65, 85),
        width=2,
    )
    y = info_origin[1] + 22
    for idx, line in enumerate(info_lines):
        font = normal_font if idx == 0 else small_font
        color = status_color if idx == 0 else (226, 232, 240)
        _draw_label(draw, (info_origin[0] + 22, y), line, font, color)
        y += 34 if idx == 0 else 26

    bottom = [
        "说明：左侧为观察者/低空斜视输入，中间为航拍参考图上的真实位置与估计位置，右侧为系统输出。",
        "CDA Route 表示该样本是直接走 Top1 快速路径，还是因置信度不足回退到 Top2 精配准。",
    ]
    y = 720
    for line in bottom:
        _draw_label(draw, (margin, y), line, small_font, (148, 163, 184))
        y += 30

    canvas.save(output_path)


def render_from_selection(
    all_results_csv: str | Path,
    selection_json: str | Path,
    dataset_root: str | Path,
    output_dir: str | Path,
) -> None:
    all_results_csv = Path(all_results_csv)
    selection_json = Path(selection_json)
    output_dir = Path(output_dir)
    rows = _load_rows(all_results_csv)
    row_by_id = {r["sample_id"]: r for r in rows}
    selection = json.loads(selection_json.read_text(encoding="utf-8-sig"))["demo_selection"]
    for group, sample_ids in selection.items():
        for sample_id in sample_ids:
            row = row_by_id[sample_id]
            render_sample_panel(
                row,
                rows,
                dataset_root,
                output_dir / group / f"{sample_id}_panel.png",
            )
