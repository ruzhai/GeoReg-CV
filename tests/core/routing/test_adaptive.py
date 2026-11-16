from __future__ import annotations

import pytest

from crossview.core.routing.adaptive import (
    AdaptiveRegistrationPolicy,
    RegistrationConfidence,
    RegistrationRoute,
)


def confidence(inliers: int, pnp_success: bool = True) -> RegistrationConfidence:
    return RegistrationConfidence(pnp_success=pnp_success, best_inliers=inliers)


def test_high_inlier_top1_is_accepted():
    policy = AdaptiveRegistrationPolicy(inlier_threshold=1000, fallback_topk=2)
    decision = policy.decide(confidence(1500))

    assert decision.accepted_top1 is True
    assert decision.route is RegistrationRoute.TOP1_FAST_PATH


def test_low_inlier_top1_falls_back():
    policy = AdaptiveRegistrationPolicy(inlier_threshold=1000, fallback_topk=2)
    decision = policy.decide(confidence(999))

    assert decision.accepted_top1 is False
    assert decision.route is RegistrationRoute.FALLBACK_TOP2


def test_pnp_failure_always_falls_back():
    policy = AdaptiveRegistrationPolicy(inlier_threshold=0, fallback_topk=5)
    decision = policy.decide(confidence(10_000, pnp_success=False))

    assert decision.accepted_top1 is False
    assert decision.route is RegistrationRoute.FALLBACK_TOP5
    assert "PnP" in decision.reason


def test_invalid_fallback_is_rejected_at_construction():
    with pytest.raises(ValueError):
        AdaptiveRegistrationPolicy(fallback_topk=3)


def test_cascade_accepts_top2_when_top1_is_weak():
    policy = AdaptiveRegistrationPolicy(inlier_threshold=1000, fallback_topk=2)
    decision = policy.decide_cascade(confidence(200), confidence(1400))

    assert decision.route is RegistrationRoute.FALLBACK_TOP2
    assert "Top2 accepted" in decision.reason
