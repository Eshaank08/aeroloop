# Adaptive evidence loop: implementation brief

## Goal

Build the smallest honest demonstration of AeroLoop's real product thesis:

> A drone does not finish when it reaches every waypoint. It finishes when it has
> collected verifiably usable inspection evidence, or it stops with
> `INSUFFICIENT_EVIDENCE`.

This milestone uses synthetic evidence derived from the existing physics trace. It
does not claim to process camera, microphone or thermal-sensor data. The interfaces
must be designed so those real sensors can replace the synthetic adapter later.

## Demo story

1. A work order requests a full nacelle sweep.
2. The existing controller flies it under seeded wind.
3. Each visited waypoint produces a synthetic capture record.
4. A deterministic quality gate rejects captures made too quickly, at a poor angle,
   with insufficient dwell, in excessive wind or with unsafe clearance.
5. Evidence gaps become structured re-capture requests.
6. A policy validator maps each request to one allow-listed mission primitive.
7. The simulator re-flies only the failed locations.
8. The flight view shows the initial run, rejected captures and targeted re-flight.
9. A single hashed inspection artifact records the complete decision chain.
10. A human approves only a passing, internally consistent artifact.

## Non-negotiable boundaries

- Synthetic captures are labelled `synthetic` everywhere, including the UI.
- The deterministic quality gate is the oracle. Devin cannot alter its thresholds or
  verdict during a mission.
- Devin may select only from bounded primitives; it never outputs motor commands or an
  arbitrary trajectory.
- The policy validator can reject Devin's request.
- The simulator/controller owns flight safety.
- The approval gate owns final release.
- Correct abstention is success. The system must emit `INSUFFICIENT_EVIDENCE` when a
  safe, policy-valid re-capture cannot clear the gap.

## Baseline and prerequisite

Build from `master` after commit `7ada94f`.

`sim/jobs.py` is not currently on `master`. It exists on the unmerged
`claude/hackathon-strategy-research-h4udzb` branch at commit `734a29a`. Reuse or
reimplement only the small deterministic work-order mapping needed for this slice;
do not merge unrelated branch content blindly.

Existing integration points:

| File | Reuse |
| --- | --- |
| `viz/mission.py` | Existing bounded mission grammar and `Mission` object. |
| `viz/flightlab.py` | Executes a mission through the real controller and returns frames, wind and clearance. |
| `viz/server.py` | API surface used by the flight view. |
| `viz/flight_view.html` | Show the evidence overlay and initial/follow-up traces. |
| `sim/report.py` | Stable JSON serialisation, hashing and integrity checks. |
| `scripts/approve.py` | Human approval gate; extend without weakening existing refusal rules. |
| `scripts/trigger_devin.py` | Reference for Devin organisation API authentication and polling. |
| `tests/test_report.py` | Existing artifact/integrity test conventions. |

## Proposed modules

Names may change if the existing structure suggests a clearer fit, but keep the
responsibilities separate.

```text
inspection/
  __init__.py
  schema.py              typed records and validation
  evidence.py            trace -> synthetic capture records
  quality.py             deterministic quality oracle
  policy.py              allow-list and request validation
  adaptive.py            initial flight -> gaps -> re-capture loop
  artifact.py            complete inspection artifact assembly
tests/
  test_evidence.py
  test_quality.py
  test_policy.py
  test_adaptive.py
  test_inspection_artifact.py
```

Prefer Python dataclasses and standard-library validation unless a new dependency has
a clear, documented benefit. Keep JSON output stable and serialisable.

## Data contracts

### Synthetic capture

One record per target waypoint:

```json
{
  "schema_version": 1,
  "capture_id": "cap-...",
  "source": "synthetic_trace",
  "waypoint_index": 7,
  "waypoint": [1.5, 2.1, 4.2],
  "captured_at_s": 12.42,
  "standoff_m": 3.01,
  "view_angle_deg": 8.4,
  "dwell_s": 0.62,
  "speed_mps": 0.31,
  "wind_mps": 1.8,
  "clearance_m": 0.91,
  "trace_frame_indexes": [610, 641],
  "sha256": "..."
}
```

Derive values from recorded trace and known nacelle geometry. Do not generate random
quality labels. The current point-mass simulator does not record drone attitude or a
camera boresight, so add an explicit deterministic synthetic camera-pose model before
computing view angle; do not infer that a camera was correctly aimed merely because a
waypoint was reached. Record that synthetic pose in the trace/capture. Hash a canonical
serialisation of the capture without its hash field.

### Quality result

```json
{
  "capture_id": "cap-...",
  "status": "good",
  "score": 0.93,
  "reasons": [],
  "threshold_version": "synthetic-v1"
}
```

Allowed statuses are `good`, `marginal`, `missing`. Every non-good result must contain
machine-readable reasons such as `speed_too_high`, `view_angle_too_oblique`,
`dwell_too_short`, `wind_too_high` or `clearance_too_low`.

### Requested capture

```json
{
  "request_id": "req-...",
  "waypoint_indexes": [7],
  "primitive": "capture_closeup",
  "reason_codes": ["speed_too_high"],
  "constraints": {
    "max_speed_mps": 0.25,
    "minimum_dwell_s": 0.8
  },
  "requested_by": "rule_engine"
}
```

Allowed primitives for this milestone:

- `capture_closeup`: revisit one or more known safe waypoints.
- `capture_orbit`: revisit a known ring/sector using existing inspection waypoints.
- `quiet_hover`: hold at a known safe waypoint for a bounded duration.
- `return_home`: end the mission safely.

The validator must reject unknown primitives, unknown waypoint indexes, coordinates
outside the known waypoint set, excessive dwell, excessive retry counts and any request
after collision or abort.

### Inspection disposition

Allowed dispositions:

- `PASS`: all required captures are good after validation and allowed retries.
- `INSUFFICIENT_EVIDENCE`: gaps remain or a re-capture cannot be executed safely.
- `ABORTED`: collision, policy violation or safety state terminated the mission.
- `AWAITING_HUMAN_APPROVAL`: evidence passed but no person has approved the artifact.
- `APPROVED`: a human approved the exact artifact digest.

## Deterministic quality gate

Start with explainable thresholds committed in code. The exact defaults should be
calibrated so seeded tests contain a mixture of good and marginal captures without
manufacturing a guaranteed demo outcome.

Evaluate at least:

- Speed during the capture window as a blur proxy.
- Angle between camera/view vector and the local nacelle surface normal.
- Continuous dwell inside the waypoint tolerance.
- Wind magnitude during the capture window.
- Minimum clearance throughout the capture window.
- Missing capture when a waypoint was never reached.

Quality classification must be reproducible for the same trace. Add boundary tests for
every threshold and property-style sweeps where practical.

## Adaptive re-capture

Implement two planners behind one interface:

```python
class RecapturePlanner:
    def plan(self, gaps, context) -> list[RequestedCapture]: ...
```

1. `RuleBasedRecapturePlanner` is required and is the default/oracle baseline.
2. `DevinRecapturePlanner` is optional until the deterministic loop passes. It consumes
   only the structured gaps and returns the same schema.

Both outputs go through the same policy validator. Record planner input, raw output,
validated output and rejection reason in the artifact.

Limit the first implementation to one follow-up round. If gaps remain afterward,
return `INSUFFICIENT_EVIDENCE`; do not create an unbounded retry loop.

## Human-in-the-loop states

The synthetic milestone needs one final approval, but the schema should reserve the
real-world gates:

- `asset_confirmation`: not exercised with the fixed synthetic nacelle.
- `safety_intervention`: emergency stop/abort remains available.
- `inspection_review`: required before changing `AWAITING_HUMAN_APPROVAL` to
  `APPROVED`.

Approval must bind the approver, time and digest of the complete pre-approval artifact.
Any later mutation invalidates integrity.

## Dynamic obstacles and audio/visual scope

Do not claim real bird detection, real visual defect detection or real acoustic
diagnosis in this milestone.

Add a minimal deterministic obstacle interruption only if the evidence loop is already
complete and tested:

- A seeded moving obstacle crosses the planned route.
- The local simulator, not Devin, pauses/aborts the mission.
- No capture is marked good through an obstacle-affected interval.
- The artifact records the interruption and disposition.

Real sensor adapters are a later replacement for `inspection/evidence.py`:

- `VisualEvidenceAdapter`: image, calibration, exposure, blur and localisation.
- `AcousticEvidenceAdapter`: WAV/PCM, microphone calibration, SNR and rotor-noise
  metadata.
- `ThermalEvidenceAdapter`: radiometric frame, emissivity and ambient baseline.

The stable capture, quality, policy and artifact contracts should survive that swap.

## Flight-view requirements

The UI must make the loop understandable without reading logs:

- Clearly label the run `SYNTHETIC EVIDENCE DEMO`.
- Colour each waypoint by evidence state: good, marginal, missing, re-captured.
- Show initial and follow-up paths distinctly.
- Display reason codes for failed captures.
- Show before/after counts, for example `21 good / 3 marginal` then `24 good`.
- Show planner identity (`rule_engine` or `devin`) and validator decision.
- Show final disposition and whether human approval is pending.

## Inspection artifact

One JSON artifact must contain:

- Work order and resolved deterministic mission.
- Controller commit/hash and dirty state.
- Threshold and policy versions.
- Initial trace digest and follow-up trace digest.
- Every synthetic capture and quality result.
- Evidence gaps.
- Planner inputs and outputs.
- Policy decisions.
- Follow-up results.
- Final disposition.
- Human approval block and integrity digest.
- Explicit `synthetic: true` at the artifact and capture levels.

Do not embed the full high-frequency trace if that makes the artifact unwieldy; store a
stable digest and a relative evidence reference while keeping the demo self-contained.

## Acceptance tests

The pull request is not complete until all of these are automated:

- [ ] Same seed produces byte-equivalent pre-approval artifact content, excluding an
      explicitly controlled timestamp if necessary.
- [ ] Every visited waypoint produces at most one initial capture record.
- [ ] Every capture digest changes if any measurement changes.
- [ ] Boundary tests exist for every quality threshold.
- [ ] Missing waypoint becomes `missing`, never silently `good`.
- [ ] Rule planner requests only failed waypoint(s).
- [ ] Unknown primitive is rejected.
- [ ] Arbitrary coordinates are rejected.
- [ ] Excessive retry/dwell is rejected.
- [ ] Collision prevents re-capture and produces `ABORTED`.
- [ ] One seeded case improves after a targeted re-capture.
- [ ] One seeded case remains `INSUFFICIENT_EVIDENCE` after the retry limit.
- [ ] A PASS cannot become APPROVED without explicit human confirmation.
- [ ] Mutation after approval fails integrity verification.
- [ ] Existing controller, report and flight-view tests continue to pass.

Run the full suite with:

```bash
python -m pytest -q
```

## Build sequence for Devin

1. Read this brief, `docs/REAL_WORLD_ROADMAP.md`, `docs/PRD.md` and the integration
   files listed above.
2. Write failing unit tests for evidence derivation, quality and policy validation.
3. Implement the synthetic evidence adapter and deterministic quality oracle.
4. Implement the rule-based planner and one-round adaptive loop.
5. Extend the artifact and approval integrity tests.
6. Expose the loop through `viz/server.py` and render it in the existing flight view.
7. Run the full test suite and fix regressions.
8. Demonstrate at least one successful re-capture and one insufficient-evidence case.
9. Only after the deterministic loop passes, add a `DevinRecapturePlanner` interface or
   integration without making external API access mandatory for tests/demo fallback.
10. Open a pull request with commands, seed values, screenshots or artifact samples and
    an explicit list of synthetic versus real capabilities.

## Implementation resources

### Repository resources

- Existing simulator and verifier: `sim/run_verifier.py`, `sim/drone_dynamics.py`,
  `sim/scenarios.py`, `sim/aircraft_geometry.py`.
- Bounded command grammar and mission runner: `viz/mission.py`, `viz/flightlab.py`.
- Local API and UI: `viz/server.py`, `viz/flight_view.html`.
- Artifact integrity and approval: `sim/report.py`, `scripts/approve.py`.
- Devin API example: `scripts/trigger_devin.py`.
- Optional work-order precedent: `sim/jobs.py` at commit `734a29a`.

### External technical resources

- Devin organisation session API and structured JSON output:
  <https://docs.devin.ai/api-reference/v3/sessions/post-organizations-sessions>
- Devin structured-output guidance:
  <https://docs.devin.ai/api-reference/v1/structured-output>
- Python `dataclasses`:
  <https://docs.python.org/3/library/dataclasses.html>
- Python `hashlib`:
  <https://docs.python.org/3/library/hashlib.html>
- Python `json` canonicalisation building blocks:
  <https://docs.python.org/3/library/json.html>
- OWASP guidance for logging and auditability:
  <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html>

### Industry and assurance context

- Donecle automated aircraft inspection products:
  <https://www.donecle.com/products/>
- Mainblades aircraft inspection automation:
  <https://www.mainblades.com/>
- EASA machine-learning approval research, including vision-based maintenance
  inspection:
  <https://www.easa.europa.eu/en/research-projects/machine-learning-application-approval>
- EASA Part-145 maintenance-data guidance:
  <https://www.easa.europa.eu/en/the-agency/faqs/part-145>

These resources inform the implementation and pitch. They do not make the synthetic
demo an approved inspection method.
