from collections.abc import Sequence
from pathlib import Path

from crossview.schema.records import GeoRegistrationRecord


def _scale(value, min_value, max_value, size, pad):
    if max_value == min_value:
        return size / 2
    return pad + (value - min_value) / (max_value - min_value) * (size - 2 * pad)


def render_position_svg(
    records: Sequence[GeoRegistrationRecord], path: str | Path, width=1200, height=900
) -> None:
    """Render a lightweight GT-vs-predicted position map as SVG."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
        return

    xs = [r.gt_x for r in records] + [r.pred_x for r in records]
    ys = [r.gt_y for r in records] + [r.pred_y for r in records]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    pad = 60

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<rect width='100%' height='100%' fill='#0f172a'/>",
        "<text x='40' y='38' fill='#e5e7eb' font-size='24' font-family='Arial'>GeoReg-CV Scene_01: GT vs Estimated Geo-position</text>",
        "<text x='40' y='68' fill='#94a3b8' font-size='15' font-family='Arial'>green = ground truth, orange = estimated, gray line = localization error</text>",
    ]
    for r in records:
        gx = _scale(r.gt_x, min_x, max_x, width, pad)
        gy = height - _scale(r.gt_y, min_y, max_y, height, pad)
        px = _scale(r.pred_x, min_x, max_x, width, pad)
        py = height - _scale(r.pred_y, min_y, max_y, height, pad)
        line_color = "#ef4444" if r.error_m > 5 else "#64748b"
        pred_color = "#ef4444" if r.error_m > 5 else "#f97316"
        parts.append(
            f"<line x1='{gx:.1f}' y1='{gy:.1f}' x2='{px:.1f}' y2='{py:.1f}' stroke='{line_color}' stroke-width='1.5' opacity='0.75'/>"
        )
        parts.append(
            f"<circle cx='{gx:.1f}' cy='{gy:.1f}' r='4' fill='#22c55e'><title>{r.sample_id} GT</title></circle>"
        )
        parts.append(
            f"<circle cx='{px:.1f}' cy='{py:.1f}' r='4' fill='{pred_color}'><title>{r.sample_id} Pred error={r.error_m:.2f}m</title></circle>"
        )
        if r.error_m > 5:
            parts.append(
                f"<text x='{px + 6:.1f}' y='{py - 6:.1f}' fill='#fecaca' font-size='12' font-family='Arial'>{r.sample_id} {r.error_m:.1f}m</text>"
            )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")
