"""Adaptive re-capture loop: initial flight, evidence, gaps, one follow-up round."""

from __future__ import annotations

from viz.flightlab import fly
from viz.mission import Mission
from inspection.evidence import derive_captures
from inspection.policy import PolicyValidator
from inspection.schema import (
    DISPOSITION_ABORTED,
    DISPOSITION_INSUFFICIENT,
    DISPOSITION_PASS,
    CAPTURE_STATUS_GOOD,
    REASON_ANGLE,
    REASON_DWELL,
    REASON_SPEED,
    AdaptiveResult,
    Capture,
    FlightResult,
    PlannerRecord,
    QualityResult,
    RequestedCapture,
)


class RecapturePlanner:
    """Base class for planners that turn evidence gaps into capture requests."""

    def plan(self, gaps: list[QualityResult], context: dict) -> list[RequestedCapture]:
        raise NotImplementedError


class RuleBasedRecapturePlanner(RecapturePlanner):
    """Deterministic baseline: one close-up per failed waypoint with tightened constraints."""

    def plan(self, gaps: list[QualityResult], context: dict) -> list[RequestedCapture]:
        seed = context.get("seed", 0)
        prefix = context.get("request_prefix", "req")
        requests = []
        for gap in sorted(gaps, key=lambda q: q.capture_id):
            reasons = list(gap.reasons)
            constraints = {}
            if REASON_SPEED in reasons or REASON_ANGLE in reasons or REASON_DWELL in reasons:
                constraints["max_speed_mps"] = 0.5
                constraints["minimum_dwell_s"] = 2.0
            else:
                # Even with only wind or clearance concerns, slow down if we can.
                constraints["minimum_dwell_s"] = 2.0

            # Locate the waypoint index from the capture_id suffix we generated.
            # This is brittle; context should carry a map. Build it here from the gap.
            index = context.get("capture_to_index", {}).get(gap.capture_id, 0)
            requests.append(RequestedCapture(
                request_id=f"{prefix}-{index:03d}-{seed}",
                waypoint_indexes=[index],
                primitive="capture_closeup",
                reason_codes=reasons,
                constraints=constraints,
                requested_by="rule_engine",
            ))
        return requests


class AdaptiveRunner:
    """One-round adaptive loop with deterministic scoring and policy validation."""

    def __init__(
        self,
        planner: RecapturePlanner | None = None,
        oracle=None,
        validator: PolicyValidator | None = None,
    ):
        self.planner = planner or RuleBasedRecapturePlanner()
        self.oracle = oracle
        self.validator = validator or PolicyValidator(max_retry=1)

    def _build_initial_mission(
        self,
        label: str,
        nacelle,
        seed: int,
        wind_scale: float,
        selected_waypoints: list[tuple[float, float, float]] | None = None,
    ) -> Mission:
        waypoints = selected_waypoints if selected_waypoints else list(nacelle.waypoints())
        return Mission(
            kind="sweep",
            waypoints=waypoints,
            start=(0.0, 0.0, 6.0),
            wind_seed=seed,
            wind_scale=wind_scale,
            label=label or "Full sweep",
            text="",
            hold_duration=8.0,
        )

    def _build_initial_flight(
        self, mission: Mission, nacelle, limits
    ) -> FlightResult:
        trace = fly(mission, nacelle=nacelle, limits=limits, stride=1)
        captures = derive_captures(
            trace, nacelle, capture_id_prefix="initial", seed=mission.wind_seed
        )
        quality = self.oracle.assess_all(captures) if self.oracle else []
        return FlightResult(trace=trace, captures=captures, quality=quality)

    def _combine_legs(self, legs: list[FlightResult]) -> dict:
        if not legs:
            return {"frames": [], "elapsed_s": 0.0, "collisions": 0, "coverage": 0.0}
        combined = dict(legs[0].trace)
        combined["frames"] = []
        combined["collisions"] = 0
        combined["coverage"] = 0.0
        elapsed = 0.0
        for leg in legs:
            trace = leg.trace
            for frame in trace.get("frames", []):
                new_frame = dict(frame)
                new_frame["t"] = round(frame["t"] + elapsed, 3)
                combined["frames"].append(new_frame)
            elapsed += trace.get("elapsed_s", 0.0)
            if trace.get("collisions", 0):
                combined["collisions"] = 1
            combined["coverage"] = max(combined["coverage"], trace.get("coverage", 0.0))
        combined["elapsed_s"] = round(elapsed, 3)
        combined["waypoints"] = list(combined["waypoints"])
        return combined

    def _select_final_captures(
        self,
        initial_captures: list[Capture],
        followup_captures: list[Capture] | None,
    ) -> list[Capture]:
        if not followup_captures:
            return list(initial_captures)
        initial_by_index = {c.waypoint_index: c for c in initial_captures}
        followup_by_index = {c.waypoint_index: c for c in followup_captures}
        final = []
        all_indexes = set(initial_by_index) | set(followup_by_index)
        for idx in sorted(all_indexes):
            followup = followup_by_index.get(idx)
            if followup and followup.captured_at_s is not None:
                final.append(followup)
            else:
                final.append(initial_by_index.get(idx, followup or Capture()))
        return final

    def run(
        self,
        work_order: str,
        nacelle,
        limits,
        seed: int = 606076,
        wind_scale: float = 1.0,
        selected_waypoints: list[tuple[float, float, float]] | None = None,
    ) -> AdaptiveResult:
        initial_mission = self._build_initial_mission(work_order, nacelle, seed, wind_scale, selected_waypoints)
        initial = self._build_initial_flight(initial_mission, nacelle, limits)

        collision = bool(initial.trace.get("collisions", 0))
        if collision:
            return AdaptiveResult(
                work_order=work_order,
                seed=seed,
                wind_scale=wind_scale,
                initial=initial,
                final_captures=list(initial.captures),
                final_quality=list(initial.quality),
                final_disposition=DISPOSITION_ABORTED,
                collision=True,
                run_label=work_order,
            )

        gaps = [q for q in initial.quality if q.status != CAPTURE_STATUS_GOOD]
        capture_to_index = {c.capture_id: c.waypoint_index for c in initial.captures}
        context = {
            "seed": seed,
            "request_prefix": "recap",
            "capture_to_index": capture_to_index,
        }
        requested = self.planner.plan(gaps, context)

        accepted_legs: list[FlightResult] = []
        policy_violations: list[str] = []
        current_t = initial.trace.get("elapsed_s", 0.0)
        start_position = tuple(initial.trace["frames"][-1]["p"])
        accepted_requests: list[RequestedCapture] = []
        policy_decisions: list[dict] = []

        for request in requested:
            if collision:
                policy_violations.append("mission already aborted")
                policy_decisions.append({"request_id": request.request_id, "decision": "rejected", "reason": "mission already aborted"})
                break
            remaining_time = limits.time_budget_s - current_t
            try:
                leg = self.validator.validate(
                    request,
                    nacelle,
                    limits,
                    start_position,
                    seed,
                    wind_scale,
                    remaining_time,
                    collision=False,
                )
            except Exception as exc:
                policy_violations.append(str(exc))
                policy_decisions.append({"request_id": request.request_id, "decision": "rejected", "reason": str(exc)})
                continue

            trace = fly(
                leg.mission,
                nacelle=leg.nacelle,
                limits=leg.limits,
                stride=1,
                start_time=current_t,
            )
            accepted_requests.append(request)
            policy_decisions.append({"request_id": request.request_id, "decision": "accepted", "primitive": request.primitive})
            accepted_legs.append(FlightResult(trace=trace, captures=[], quality=[]))

            if trace["frames"]:
                start_position = tuple(trace["frames"][-1]["p"])
            current_t += trace.get("elapsed_s", 0.0)
            if trace.get("collisions", 0):
                collision = True

        followup_trace = self._combine_legs(accepted_legs)
        if followup_trace.get("waypoints") and len(followup_trace["waypoints"]) != len(nacelle.waypoints()):
            followup_trace["waypoints"] = list(nacelle.waypoints())
        followup_captures = derive_captures(
            followup_trace, nacelle, capture_id_prefix="followup", seed=seed
        ) if accepted_legs else []
        # Only the requested indexes count as real follow-up attempts; blank out
        # the others so the final selector does not treat missing unrequested
        # waypoints as failed re-captures.
        requested_indexes = set()
        for request in accepted_requests:
            requested_indexes.update(request.waypoint_indexes)
        blanked_followup = []
        for c in followup_captures:
            if c.waypoint_index in requested_indexes:
                blanked_followup.append(c)
            else:
                blanked_followup.append(Capture(
                    capture_id="followup-blank-" + c.capture_id,
                    waypoint_index=c.waypoint_index,
                    waypoint=c.waypoint,
                    source="synthetic_trace",
                    synthetic=True,
                    trace_frame_indexes=[],
                    sha256="",
                ))
        followup_quality = self.oracle.assess_all(blanked_followup) if self.oracle else []

        final_captures = self._select_final_captures(initial.captures, blanked_followup)
        final_quality = self.oracle.assess_all(final_captures) if self.oracle else []

        if collision:
            final_disposition = DISPOSITION_ABORTED
        elif all(q.status == CAPTURE_STATUS_GOOD for q in final_quality):
            final_disposition = DISPOSITION_PASS
        else:
            final_disposition = DISPOSITION_INSUFFICIENT

        return AdaptiveResult(
            work_order=work_order,
            seed=seed,
            wind_scale=wind_scale,
            initial=initial,
            gaps=gaps,
            requested=requested,
            accepted=accepted_requests,
            policy_violations=policy_violations,
            followup_legs=[leg.trace for leg in accepted_legs],
            followup_result=FlightResult(
                trace=followup_trace,
                captures=blanked_followup,
                quality=followup_quality,
            ) if accepted_legs else None,
            final_captures=final_captures,
            final_quality=final_quality,
            final_disposition=final_disposition,
            collision=collision,
            planner=self.planner.__class__.__name__,
            threshold_version=getattr(self.oracle, "version", "synthetic-v1"),
            threshold_values=(self.oracle.thresholds if self.oracle else {}),
            run_label=work_order,
        )
