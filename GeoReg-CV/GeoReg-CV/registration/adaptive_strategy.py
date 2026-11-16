from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RegistrationRoute(str, Enum):
    """Execution route selected by the adaptive registration policy."""

    TOP1_FAST_PATH = "top1_fast_path"
    FALLBACK_TOP2 = "fallback_top2"
    FALLBACK_TOP5 = "fallback_top5"
    FALLBACK_TOP5_AFTER_TOP2 = "fallback_top5_after_top2"


@dataclass(frozen=True)
class RegistrationConfidence:
    """Confidence cues available after matching and geometric localization."""

    pnp_success: bool
    best_inliers: int
    reprojection_error: Optional[float] = None
    matching_score: Optional[float] = None


@dataclass(frozen=True)
class AdaptiveDecision:
    """Decision made by the confidence-driven adaptive policy."""

    route: RegistrationRoute
    accepted_top1: bool
    reason: str
    threshold: int
    best_inliers: int


class ConfidenceEvaluator:
    """Evaluate whether a fast Top1 localization result is reliable enough.

    The first version uses matching inlier count because it is available in the
    current AnyVisLoc result files and does not require ground-truth position.
    Ground-truth-only quantities such as localization error or retrieval_gt_rank
    must not be used in online deployment.
    """

    def __init__(self, inlier_threshold: int = 1000):
        self.inlier_threshold = inlier_threshold

    def is_confident(self, confidence: RegistrationConfidence) -> tuple[bool, str]:
        if not confidence.pnp_success:
            return False, "PnP failed"
        if confidence.best_inliers < self.inlier_threshold:
            return False, f"best_inliers {confidence.best_inliers} < threshold {self.inlier_threshold}"
        return True, f"best_inliers {confidence.best_inliers} >= threshold {self.inlier_threshold}"


class AdaptiveRegistrationPolicy:
    """Confidence-driven adaptive fast registration policy.

    Policy:
        1. Run Top1 fast path first.
        2. Accept Top1 if confidence is high.
        3. Otherwise fallback to a more robust Top2 or Top5 path.
    """

    def __init__(self, inlier_threshold: int = 1000, fallback_topk: int = 2):
        if fallback_topk not in (2, 5):
            raise ValueError("fallback_topk must be 2 or 5")
        self.evaluator = ConfidenceEvaluator(inlier_threshold)
        self.inlier_threshold = inlier_threshold
        self.fallback_topk = fallback_topk

    def decide(self, top1_confidence: RegistrationConfidence) -> AdaptiveDecision:
        confident, reason = self.evaluator.is_confident(top1_confidence)
        if confident:
            return AdaptiveDecision(
                route=RegistrationRoute.TOP1_FAST_PATH,
                accepted_top1=True,
                reason=reason,
                threshold=self.inlier_threshold,
                best_inliers=top1_confidence.best_inliers,
            )

        route = RegistrationRoute.FALLBACK_TOP2 if self.fallback_topk == 2 else RegistrationRoute.FALLBACK_TOP5
        return AdaptiveDecision(
            route=route,
            accepted_top1=False,
            reason=reason,
            threshold=self.inlier_threshold,
            best_inliers=top1_confidence.best_inliers,
        )

    def decide_cascade(
        self,
        top1_confidence: RegistrationConfidence,
        top2_confidence: RegistrationConfidence,
    ) -> AdaptiveDecision:
        """Decide the route for the Top1 -> Top2 -> Top5 cascade."""
        top1_confident, top1_reason = self.evaluator.is_confident(top1_confidence)
        if top1_confident:
            return AdaptiveDecision(
                route=RegistrationRoute.TOP1_FAST_PATH,
                accepted_top1=True,
                reason=top1_reason,
                threshold=self.inlier_threshold,
                best_inliers=top1_confidence.best_inliers,
            )

        top2_confident, top2_reason = self.evaluator.is_confident(top2_confidence)
        if top2_confident:
            return AdaptiveDecision(
                route=RegistrationRoute.FALLBACK_TOP2,
                accepted_top1=False,
                reason=f"Top1 rejected ({top1_reason}); Top2 accepted ({top2_reason})",
                threshold=self.inlier_threshold,
                best_inliers=top2_confidence.best_inliers,
            )

        return AdaptiveDecision(
            route=RegistrationRoute.FALLBACK_TOP5_AFTER_TOP2,
            accepted_top1=False,
            reason=f"Top1 rejected ({top1_reason}); Top2 rejected ({top2_reason})",
            threshold=self.inlier_threshold,
            best_inliers=top2_confidence.best_inliers,
        )


def build_confidence_from_result_row(row: dict) -> RegistrationConfidence:
    """Build confidence from an AnyVisLoc-style result row."""

    pnp_value = row.get("pnp_success", True)
    if isinstance(pnp_value, str):
        pnp_success = pnp_value.strip().lower() in {"true", "1", "yes"}
    else:
        pnp_success = bool(pnp_value)

    try:
        best_inliers = int(float(row.get("best_inliers", 0)))
    except Exception:
        best_inliers = 0

    reprojection_error = row.get("reprojection_error", None)
    try:
        reprojection_error = float(reprojection_error) if reprojection_error not in ("", None) else None
    except Exception:
        reprojection_error = None

    return RegistrationConfidence(
        pnp_success=pnp_success,
        best_inliers=best_inliers,
        reprojection_error=reprojection_error,
    )
