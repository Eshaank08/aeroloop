"""Deterministic quality oracle for synthetic inspection captures."""

from inspection.schema import (
    REASON_ANGLE,
    REASON_CLEARANCE,
    REASON_DWELL,
    REASON_MISSING,
    REASON_SPEED,
    REASON_WIND,
    CAPTURE_STATUS_GOOD,
    CAPTURE_STATUS_MARGINAL,
    CAPTURE_STATUS_MISSING,
    Capture,
    QualityResult,
)

DEFAULT_THRESHOLDS = {
    "max_speed_mps": 1.0,
    "max_view_angle_deg": 40.0,
    "min_dwell_s": 0.4,
    "max_wind_mps": 5.0,
    "min_clearance_m": 0.3,
    "threshold_version": "synthetic-v1",
}


class QualityOracle:
    """Explainable, deterministic classifier for capture quality."""

    def __init__(self, thresholds: dict | None = None):
        self.thresholds = dict(thresholds) if thresholds else dict(DEFAULT_THRESHOLDS)
        self.version = self.thresholds.get("threshold_version", "synthetic-v1")

    def assess(self, capture: Capture) -> QualityResult:
        reasons = []

        if capture.captured_at_s is None and not capture.trace_frame_indexes:
            return QualityResult(
                capture_id=capture.capture_id,
                status=CAPTURE_STATUS_MISSING,
                score=0.0,
                reasons=[REASON_MISSING],
                threshold_version=self.version,
            )

        if capture.speed_mps is not None and capture.speed_mps > self.thresholds["max_speed_mps"]:
            reasons.append(REASON_SPEED)
        if capture.view_angle_deg is not None and capture.view_angle_deg > self.thresholds["max_view_angle_deg"]:
            reasons.append(REASON_ANGLE)
        if capture.dwell_s is not None and capture.dwell_s < self.thresholds["min_dwell_s"]:
            reasons.append(REASON_DWELL)
        if capture.wind_mps is not None and capture.wind_mps > self.thresholds["max_wind_mps"]:
            reasons.append(REASON_WIND)
        if capture.clearance_m is not None and capture.clearance_m < self.thresholds["min_clearance_m"]:
            reasons.append(REASON_CLEARANCE)

        if not reasons:
            return QualityResult(
                capture_id=capture.capture_id,
                status=CAPTURE_STATUS_GOOD,
                score=1.0,
                reasons=[],
                threshold_version=self.version,
            )

        penalty = 0.2 * len(reasons)
        score = max(0.1, 0.8 - penalty)
        return QualityResult(
            capture_id=capture.capture_id,
            status=CAPTURE_STATUS_MARGINAL,
            score=round(score, 3),
            reasons=reasons,
            threshold_version=self.version,
        )

    def assess_all(self, captures: list[Capture]) -> list[QualityResult]:
        return [self.assess(c) for c in captures]
