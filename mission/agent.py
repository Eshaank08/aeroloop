"""The autonomous mission loop: Devin chooses every action, the verifier judges.

Nothing here selects an inspection target. When the agent is unreachable or keeps
proposing actions outside the safety envelope, the mission performs a bounded safe
stop and reports insufficient evidence. It never finishes the sweep on its own and
it never claims PASS on the agent's behalf.
"""

from __future__ import annotations

import json

from mission.contract import (
    ACTION_SCHEMA,
    CLAIM_ABORT,
    CLAIM_COMPLETE,
    PRIMITIVE_ABORT,
    PRIMITIVE_COMPLETE,
    PRIMITIVE_RETURN_HOME,
    SCHEMA_VERSION,
    TERMINAL_PRIMITIVES,
    Action,
    ContractError,
    action_to_dict,
    observation_to_dict,
    outcome_to_dict,
    packet_digest,
    parse_action,
)
from mission.episode import MissionEpisode
from mission.safety import Decision, MissionPolicyViolation, MissionSafetyEnvelope

DISPOSITION_PASS = "PASS"
DISPOSITION_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
DISPOSITION_ABORTED = "ABORTED"

MAX_ACTIONS = 24
MAX_CONSECUTIVE_REJECTIONS = 3
SAFE_STOP_DURATION_S = 6.0

MISSION_BRIEF = """You are the mission agent for AeroLoop, an autonomous drone inspection of an
aircraft engine nacelle. You choose every mission action. A separate flight
controller stabilises the vehicle and executes what you choose.

Your goal is complete photographic evidence: every authorised waypoint must be
inspected. A waypoint counts as inspected only when the drone is within 0.5 m of
it, the camera is aimed within 60 degrees of the nacelle surface, and the shot is
steady (body rate at most 1.5 rad/s and speed at most 2.5 m/s).

You will receive observations describing only what the drone can sense. You will
not be told the wind schedule or the verifier's answer. After each action you get
a new observation reporting what evidence was gained and what is still missing.
The `events` list may also contain clearly labelled synthetic visual or acoustic
detections used by this simulator. Treat an obstacle safety stop as authoritative;
never try to override it. In real deployment these events come from onboard sensors.

Rules:
- Answer with structured output only, matching the action schema exactly.
- Never ask a question. Nobody is reading this session and no answer will come.
  If you are unsure, choose the safest useful action instead.
- Every action must set observation_id to the observation you are answering.
- Every action_id must be unique within the mission.
- Choose inspect_waypoints for evidence, quiet_hover to settle before a difficult
  shot, return_home to stop safely, complete or abort to end the mission.
- For every inspect_waypoints or quiet_hover action, choose max_speed_mps and
  view_distance_m inside the published limits. Use a slower, closer view for fine
  evidence and a wider, faster view for coverage when conditions allow.
- An action may be rejected by the safety envelope. You will be told why. Choose a
  different action; the system will not choose one for you.
- Prefer few, well chosen actions. Time and attempts per waypoint are limited.

Every observation carries a `limits` block with the hard bounds your action must
satisfy: the longest single action, the most targets in one action, the attempts
left per waypoint and the vehicle speed limit. An action outside those bounds is
rejected and wastes a turn, so read them before choosing.
"""


class MissionPlannerError(RuntimeError):
    """Raised when the agent cannot be reached or cannot produce a decision."""


class DevinMissionPlanner:
    """Asks a live Devin session for every mission action."""

    name = "devin"

    def __init__(self, session, brief: str = MISSION_BRIEF, work_order: str = ""):
        self.session = session
        self.brief = brief
        self.work_order = work_order

    @property
    def metadata(self) -> dict:
        return {
            "provider": "devin",
            "session_id": self.session.session_id,
            "session_url": self.session.session_url,
            "status": self.session.status,
        }

    def decide(self, observation, rejection: str | None = None) -> dict:
        packet = observation_to_dict(observation)
        if rejection:
            packet["previous_action_rejected"] = rejection
        message = json.dumps(packet, sort_keys=True)
        # The operator's own words, unedited. The authorised waypoint set in the
        # observation is the hard boundary; this is the intent inside it.
        order = (
            f"\n\nThe operator asked for this, in their words:\n"
            f"  \"{self.work_order}\"\n"
            "That sentence has already been translated into the authorised waypoint set "
            "you can see in the observation. The translation is the operator's, not "
            "yours, so treat the authorised set as the definition of the job: the "
            "inspection is complete only when every one of those waypoints has been "
            "inspected. Do not narrow it further because you read the sentence "
            "differently, and do not claim complete while available_targets is "
            "non-empty. If some waypoint genuinely cannot be captured, say so with "
            "insufficient_evidence or needs_human rather than calling the mission done.\n"
            if self.work_order else ""
        )
        prompt = (
            f"{self.brief}{order}\nAction schema:\n"
            f"{json.dumps(ACTION_SCHEMA, sort_keys=True)}\n\nFirst observation:\n{message}"
        )

        def matches(output: dict) -> bool:
            return output.get("observation_id") == observation.observation_id

        nudge = (
            f"Structured output only. Answer observation {observation.observation_id} "
            "with one action that satisfies the limits block. Do not ask questions."
        )
        try:
            return self.session.decide(prompt, message, matches, nudge=nudge)
        except Exception as exc:
            raise MissionPlannerError(str(exc)) from exc


class ScriptedPilot:
    """Deterministic local baseline, for tests and for measuring Devin against.

    This is not the challenge demo. It exists so the mission loop can be tested
    without spending API credits, and so there is a labelled comparison number.
    """

    name = "scripted_baseline"
    metadata = {"provider": "local", "mode": "deterministic_baseline"}

    def __init__(self, batch_size: int = 4):
        self.batch_size = batch_size
        self.counter = 0

    def decide(self, observation, rejection: str | None = None) -> dict:
        self.counter += 1
        remaining = list(observation.available_targets)
        if not remaining:
            return {
                "schema_version": SCHEMA_VERSION,
                "observation_id": observation.observation_id,
                "action_id": f"baseline-{self.counter}",
                "primitive": PRIMITIVE_COMPLETE,
                "reason": "every authorised waypoint has been inspected",
                "claim": CLAIM_COMPLETE,
                "confidence": 1.0,
            }
        # The comparison pilot deliberately exercises the same bounded control
        # surface as Devin so the UI can be tested without API credits.
        profiles = ((0.8, 1.0), (1.4, 1.6), (1.1, 1.3))
        speed, view_distance = profiles[(self.counter - 1) % len(profiles)]
        return {
            "schema_version": SCHEMA_VERSION,
            "observation_id": observation.observation_id,
            "action_id": f"baseline-{self.counter}",
            "primitive": "inspect_waypoints",
            "waypoint_indexes": remaining[: self.batch_size],
            "constraints": {
                "duration_s": 30.0,
                "max_speed_mps": speed,
                "view_distance_m": view_distance,
            },
            "reason": "collect evidence for the next batch of missing waypoints",
            "confidence": 0.5,
        }


class MissionRun:
    """The full record of one autonomous mission."""

    def __init__(self, mission_id: str, seed: int, planner_name: str):
        self.mission_id = mission_id
        self.seed = seed
        self.planner_name = planner_name
        self.steps: list[dict] = []
        self.planner_failed = False
        self.planner_failures: list[str] = []
        self.rejections: list[str] = []
        self.agent_claim = ""
        self.safe_stop = False
        self.verification: dict = {}
        self.disposition = DISPOSITION_INSUFFICIENT
        self.planner_metadata: dict = {}

    def to_dict(self) -> dict:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "mission_id": self.mission_id,
            "seed": self.seed,
            "synthetic": True,
            "planner": self.planner_name,
            "planner_metadata": self.planner_metadata,
            "planner_failed": self.planner_failed,
            "planner_failures": self.planner_failures,
            "rejections": self.rejections,
            "agent_claim": self.agent_claim,
            "safe_stop": self.safe_stop,
            "steps": self.steps,
            "verification": self.verification,
            "final_disposition": self.disposition,
        }
        payload["integrity_digest"] = packet_digest(payload)
        return payload


def _safe_stop(episode: MissionEpisode, run: MissionRun, reason: str) -> None:
    """Bounded return toward home, flown by the controller, then end the mission.

    This is a safety mechanism, not a mission decision. It collects no new
    evidence and it cannot turn a failed mission into a passing one.
    """
    run.safe_stop = True
    if episode.closed:
        return
    action = Action(
        observation_id=episode.observation_id,
        action_id=f"safe-stop-{episode.observation_id}",
        primitive=PRIMITIVE_RETURN_HOME,
        reason=reason,
        chosen_by="safety_envelope",
    )
    outcome = episode.act(action, SAFE_STOP_DURATION_S)
    run.steps.append({
        "observation_id": episode.observation_id,
        "action": action_to_dict(action),
        "decision": Decision(
            accepted=True,
            duration_s=SAFE_STOP_DURATION_S,
            reason=reason,
            action_id=action.action_id,
            primitive=action.primitive,
        ).to_dict(),
        "outcome": outcome_to_dict(outcome),
    })
    episode.close()


def run_mission(
    planner,
    seed: int,
    authorised_indexes: list[int] | None = None,
    max_actions: int = MAX_ACTIONS,
    episode: MissionEpisode | None = None,
) -> MissionRun:
    episode = episode or MissionEpisode(seed=seed, authorised_indexes=authorised_indexes)
    envelope = MissionSafetyEnvelope(
        authorised_indexes=episode.authorised_indexes,
        max_speed_mps=episode.params.max_speed,
    )
    run = MissionRun(episode.mission_id, seed, getattr(planner, "name", type(planner).__name__))

    previous_action_id = ""
    last_outcome: dict | None = None
    rejection: str | None = None
    consecutive_rejections = 0

    while not episode.closed and len(
        [s for s in run.steps if s.get("decision", {}).get("decision") == "accepted"]
    ) < max_actions:
        observation = episode.observe(
            previous_action_id=previous_action_id,
            last_outcome=last_outcome,
            actions_remaining=max_actions - episode.actions_executed,
            limits=envelope.limits(episode.time_remaining_s),
        )
        step: dict = {
            "observation_id": observation.observation_id,
            "observation": observation_to_dict(observation),
        }
        step["observation_digest"] = packet_digest(step["observation"])

        try:
            payload = planner.decide(observation, rejection)
        except MissionPlannerError as exc:
            run.planner_failed = True
            run.planner_failures.append(str(exc))
            step["planner_error"] = str(exc)
            run.steps.append(step)
            _safe_stop(episode, run, f"agent unreachable: {exc}")
            break

        rejection = None
        try:
            action = parse_action(payload, chosen_by=run.planner_name)
            step["action"] = action_to_dict(action)
            step["action_digest"] = packet_digest(step["action"])
            decision = envelope.validate(action, observation, episode.time_remaining_s)
        except (ContractError, MissionPolicyViolation) as exc:
            consecutive_rejections += 1
            rejection = str(exc)
            run.rejections.append(rejection)
            step["decision"] = Decision(
                accepted=False,
                reason=rejection,
                action_id=str(payload.get("action_id", "")) if isinstance(payload, dict) else "",
                primitive=str(payload.get("primitive", "")) if isinstance(payload, dict) else "",
            ).to_dict()
            run.steps.append(step)
            if consecutive_rejections >= MAX_CONSECUTIVE_REJECTIONS:
                _safe_stop(
                    episode, run,
                    f"{consecutive_rejections} consecutive unsafe or malformed actions",
                )
                break
            continue

        consecutive_rejections = 0
        step["decision"] = decision.to_dict()

        if action.primitive in TERMINAL_PRIMITIVES:
            run.agent_claim = action.claim
            run.steps.append(step)
            if action.primitive == PRIMITIVE_ABORT:
                _safe_stop(episode, run, f"agent aborted: {action.reason}")
            episode.close()
            break

        outcome = episode.act(action, decision.duration_s)
        step["outcome"] = outcome_to_dict(outcome)
        step["execution"] = dict(episode.last_execution)
        run.steps.append(step)
        previous_action_id = action.action_id
        last_outcome = step["outcome"]

    run.planner_metadata = dict(getattr(planner, "metadata", {}))
    run.verification = episode.verify()

    safety_failures = {
        "collision", "ground_contact", "dynamic_obstacle_proximity", "unsafe_speed",
    }
    if run.verification["failure"] in safety_failures or run.agent_claim == CLAIM_ABORT:
        run.disposition = DISPOSITION_ABORTED
    elif run.planner_failed:
        # The authority that decides what to inspect never answered. The mission
        # cannot be called complete no matter how much evidence happens to exist.
        run.disposition = DISPOSITION_INSUFFICIENT
    elif run.verification["passed"]:
        run.disposition = DISPOSITION_PASS
    else:
        run.disposition = DISPOSITION_INSUFFICIENT

    return run
