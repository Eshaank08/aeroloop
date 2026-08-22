# Real-world multimodal inspection roadmap

## Purpose

AeroLoop currently proves that Devin can write a flight controller and improve it
against an adversarial simulator. The real product must go further: an inspection
drone should understand what is actually present, collect evidence in several
modalities, adapt its inspection when the scene differs from the plan, and produce a
traceable package for a qualified inspector.

This document is the implementation backlog for moving from the simulator to a real
hangar. It is deliberately not a claim that an AI system can release an aircraft to
service. The system gathers and organises evidence; approved maintenance data and
qualified personnel remain authoritative.

## Target workflow

1. Discover and describe an unexpected object.
2. Read markings and establish probable identity.
3. Ask a human to confirm the asset.
4. Retrieve the approved inspection procedure for the confirmed configuration.
5. Gather visual, thermal, acoustic, depth and flight-telemetry evidence.
6. Adaptively request better viewpoints or quiet audio captures.
7. Highlight anomalies, contradictory evidence and uncertainty.
8. Leave final disposition and return-to-service approval to qualified personnel.

The system must be useful when the expected engine is absent, the wrong component is
present, the serial number is unreadable, or an unknown object appears in the work
area. In every case, uncertainty is an explicit output rather than something hidden by
a confident description.

## System boundary

```text
operator / work order / approved maintenance data
                      |
                      v
              mission control backend
              |       |            |
              |       |            +--> Devin inspection session
              |       |                 planning, synthesis, code changes
              |       |
              |       +--> perception services
              |            vision, OCR, thermal, depth, acoustics
              |
              +--> policy + evidence verifier
                       |
             validated mission requests only
                       |
                       v
             onboard safety supervisor
             planner, avoidance, geofence,
             emergency stop, return/land
                       |
                       v
                 drone + sensors
```

### Onboard, deterministic and safety critical

- Stabilisation, state estimation and flight control.
- Collision avoidance, propeller clearance and speed/acceleration limits.
- Geofence, loss-of-link behaviour, emergency stop and controlled landing.
- Sensor triggering with timestamps and calibration metadata.
- A command allow-list. The drone accepts bounded inspection primitives such as
  `capture_orbit`, `capture_closeup`, `quiet_hover`, `return_home` and `land`; it does
  not accept arbitrary trajectories or motor commands from a language model.
- Local operation without Devin or cloud connectivity. Loss of the backend must cause
  a safe hold, return or landing, never continued improvisation.

### Inspection backend, measurable and replaceable

- Evidence ingestion and immutable object storage.
- Camera calibration, image quality and blur checks.
- Open-vocabulary object proposals plus a separate unknown-object detector.
- OCR/barcode/serial-number extraction and asset-registry matching.
- Defect localisation from task-specific vision models.
- Thermal calibration and hotspot comparison against relevant baselines.
- Acoustic preprocessing, drone self-noise cancellation and anomaly scoring.
- Time synchronisation between imagery, audio, thermal data and telemetry.
- Maintenance-manual retrieval restricted by confirmed aircraft/component
  configuration and revision.
- Confidence calibration, contradiction detection and abstention.
- Cryptographic hashes, model versions and provenance for every derived observation.

### Devin, adaptive but not authoritative

Use Devin for work that benefits from long-horizon reasoning and software access:

- Turn structured observations into a proposed inspection plan.
- Identify missing evidence and request a bounded follow-up capture.
- Compare observations with approved procedure text supplied by the backend.
- Produce structured findings, open questions and a human-readable report.
- Build or update asset-specific inspection adapters in the repository, run their
  tests and open a pull request.
- Investigate verifier failures and improve non-safety-critical orchestration code.

Do not use Devin for:

- The inner flight-control loop or direct motor commands.
- Collision avoidance or emergency response.
- Unsupervised asset confirmation.
- Selecting an unofficial inspection procedure.
- Declaring a component airworthy or releasing an aircraft to service.

The current `scripts/trigger_devin.py` pattern should be extended, not discarded.
Create a Devin session through the organisation API, attach a bounded evidence bundle,
require a JSON Schema output, poll the session, and validate the response before the
mission service can act on it. A reusable Devin playbook should encode the inspection
rules and escalation policy.

Example Devin output contract:

```json
{
  "asset": {
    "candidate_type": "hydraulic pump",
    "candidate_serial": "HP-2048",
    "identity_confidence": 0.71,
    "human_confirmation_required": true
  },
  "observations": [],
  "contradictions": [],
  "requested_capture": {
    "primitive": "quiet_hover",
    "target_region": "aft bearing housing",
    "duration_s": 8,
    "reason": "insufficient acoustic signal-to-noise ratio"
  },
  "procedure_reference": null,
  "disposition": "INSUFFICIENT_EVIDENCE"
}
```

## End-to-end field operation

### 1. Prepare

- Import the work order and aircraft/component configuration.
- Resolve current approved maintenance data before flight.
- Record hangar geometry, exclusion zones, personnel zones and escape routes.
- Verify drone, prop guards, batteries, sensors, storage and calibrations.
- Run a preflight self-test and obtain permission from the responsible hangar/MRO
  authority.

### 2. Establish the scene

- Perform a slow, stand-off mapping pass.
- Detect people, aircraft surfaces, stands, cables, tools and unexpected objects.
- Compare the observed scene with the work order without assuming the work order is
  correct.
- Stop for human confirmation when the primary asset identity is uncertain or
  inconsistent.

### 3. Bind an approved procedure

- Read serial numbers, placards and configuration markers.
- Match them against the operator/MRO asset system.
- Require a human to confirm the selected asset.
- Retrieve the approved procedure and exact revision for that asset.
- Compile the procedure into bounded evidence requirements: locations, resolution,
  lighting, angles, dwell time, temperature and acoustic conditions.

### 4. Acquire evidence adaptively

- Execute only policy-approved capture primitives.
- Score evidence quality immediately.
- If a view is occluded, blurred or poorly lit, request a safer alternative viewpoint.
- For acoustics, land or hover at a predefined quiet measurement point when rotor noise
  prevents a useful capture. Never pretend a noisy recording is diagnostic.
- Preserve raw evidence even when a derived model result is later rejected.

### 5. Analyse and verify

- Run specialist models independently by modality.
- Require localisation for visual findings and time/frequency localisation for audio.
- Compare findings with prior inspections when the operator permits it.
- Treat disagreement between models as a review trigger, not a voting exercise.
- Run evidence completeness, provenance and policy checks before generating a report.

### 6. Review and release

- Show the inspector every finding beside its source evidence, confidence, model
  version and relevant procedure step.
- Allow the inspector to accept, reject, relabel or request another capture.
- Sign the immutable inspection artifact after review.
- Keep return-to-service approval in the organisation's approved maintenance process;
  AeroLoop records the decision but does not make it.

## Verification strategy

Simulation remains necessary but is only the first rung of the evidence ladder.

1. **Software tests:** schemas, policy rules, evidence hashes and deterministic replay.
2. **Perception benchmarks:** labelled images/audio/thermal sequences with separate
   known, difficult and genuinely unknown assets.
3. **Hardware-in-the-loop:** real autopilot and sensors against simulated geometry and
   failures.
4. **Instrumented mock-up:** stationary components in a controlled cage with seeded
   defects and obstacles.
5. **Hangar shadow mode:** fly and report, but compare all output with an inspector and
   make no operational decision.
6. **Constrained assisted operation:** approved asset/procedure combinations with
   mandatory review of every finding.
7. **Expanded operational approval:** only after documented performance, change
   control and agreement with the operator, OEM and competent authority where needed.

Every stage needs predefined acceptance criteria. Aggregate accuracy is insufficient;
track false-negative rate by defect type, false positives, unknown-object abstention,
identity errors, evidence completeness, collision/near-miss rate, mission aborts,
latency and inspector disagreement.

## Challenges, implications and mitigations

| Challenge | Real-world implication | Required mitigation / backlog |
| --- | --- | --- |
| Open-world recognition | A plausible label can be wrong, especially for visually similar components. | Separate detection from identity; use markings and registry data; calibrate confidence; require confirmation; support `UNKNOWN`. |
| Missing or incorrect work-order data | The system may bind the wrong manual or inspect the wrong configuration. | Compare observed markings with configuration records and block procedure selection on mismatch. |
| Model hallucination | Fluent findings can outrun the evidence. | Require structured outputs, evidence IDs and localisations; reject claims with missing provenance. |
| Rare defect data | Safety-relevant defects may have too few examples for reliable learning. | OEM/MRO data partnerships, controlled seeded defects, synthetic augmentation, strict holdout sets and shadow deployment. |
| Domain shift | New lighting, paint, dirt, weather, camera or aircraft types change performance. | Quality gates, per-site validation, drift monitoring and versioned operating envelopes. |
| Drone acoustic self-noise | Propellers can mask the machine signature and create false conclusions. | Directional/microphone arrays, rotor-noise cancellation, baseline recordings and quiet capture primitives; abstain below SNR threshold. |
| Thermal ambiguity | Reflections, emissivity and recent operation can look like defects. | Calibration targets, ambient/operating-state metadata and component-specific baselines. |
| Occlusion and limited access | A complete-looking scan may omit critical surfaces. | Procedure-derived coverage maps, explicit blind spots and inspector-visible completeness metrics. |
| Collision and foreign-object risk | A small navigation error can damage an aircraft or injure staff. | Prop guards, stand-off limits, independent avoidance, exclusion zones, emergency stop and incremental flight envelope expansion. |
| People entering the area | Dynamic hangar work invalidates a planned path. | Person detection is not the only control: physical barriers, spotter/area owner, policy stop and restart after scene validation. |
| Cloud/network loss | Remote reasoning may stall during flight. | Safe local autonomy, queued evidence upload and no dependency on Devin for stabilisation or emergency action. |
| Latency | Long model/Devin calls cannot support control loops. | Asynchronous mission state machine; bounded capture requests; timeouts and safe fallback states. |
| Cybersecurity | Sensor, manual or command tampering can corrupt a safety decision. | Mutual authentication, signed commands/artifacts, least privilege, isolated flight network, audit logs and supply-chain controls. |
| Data ownership/privacy | Aircraft imagery, serial numbers, voices and maintenance records are sensitive. | Customer-controlled retention, encryption, regional storage, access logs, redaction and explicit model-training policy. |
| Model/vendor updates | A silent model change can invalidate prior validation. | Pin model/version/configuration, regression gates, change approval and reproducible evidence replay. |
| Human automation bias | Inspectors may accept confident AI output without checking evidence. | Uncertainty-first UI, forced review of critical evidence, disagreement sampling and training. |
| Regulatory acceptance | A useful tool is not automatically an approved maintenance method. | Map each use case to approved maintenance data, quality procedures and competent-authority/OEM acceptance; begin as decision support. |
| Return-to-service authority | Software cannot replace authorised certification privileges. | Keep disposition and release with qualified personnel; record identity, signature, scope and referenced maintenance data. |
| Product liability and insurance | Damage or a missed defect has financial and safety consequences. | Defined responsibility matrix, operational limits, incident logs, contractual allocation and appropriate insurance. |

## Implementation backlog

### Phase 0 — product and safety definition

- [ ] Choose one first asset and procedure, such as an off-wing engine exterior visual
      inspection. Do not start with “anything in any hangar.”
- [ ] Select the launch jurisdiction, MRO/operator partner and accountable maintenance
      organisation.
- [ ] Write the concept of operations, responsibility matrix and system safety analysis.
- [ ] Define inspection claims: evidence collection, decision support, defect screening
      or approved inspection method.
- [ ] Define the operating envelope, abort conditions and human roles.
- [ ] Agree data ownership, retention, security and model-training restrictions.

### Phase 1 — evidence platform

- [ ] Add versioned schemas for missions, assets, observations, capture requests,
      findings, procedures, approvals and signed evidence manifests.
- [ ] Build immutable evidence storage with checksums and timestamps.
- [ ] Record calibration, sensor, model, code and manual versions in every artifact.
- [ ] Extend `sim/report.py` from controller-only metadata to a multimodal inspection
      manifest.
- [ ] Extend `scripts/approve.py` with separate asset-confirmation, inspection-review
      and flight-release gates.
- [ ] Build deterministic replay: the same evidence bundle must reproduce the same
      non-generative measurements and policy decisions.

### Phase 2 — multimodal perception

- [ ] Camera quality, blur, exposure and coverage checks.
- [ ] Open-vocabulary detection plus unknown-object rejection.
- [ ] OCR/barcode/serial parsing with geometric source regions.
- [ ] Asset-registry matching with ambiguity and mismatch states.
- [ ] Task-specific visual defect models with localisation.
- [ ] Radiometric thermal ingestion and calibration.
- [ ] Audio capture, synchronisation, noise profiling and anomaly detection.
- [ ] Cross-modal contradiction detection without hiding individual model outputs.
- [ ] Curate benchmark datasets and publish model cards/operating limits internally.

### Phase 3 — Devin inspection orchestration

- [ ] Add `scripts/trigger_devin_inspection.py` using the Devin organisation API.
- [ ] Upload only a bounded evidence bundle; keep raw/customer-sensitive data under
      explicit policy.
- [ ] Require a self-contained JSON Schema for Devin's output.
- [ ] Create an AeroLoop inspection playbook containing abstention, evidence citation,
      procedure and escalation rules.
- [ ] Add a policy validator that converts an accepted `requested_capture` into a safe
      mission primitive or rejects it with a reason.
- [ ] Persist Devin session ID, input hashes, structured output and policy decision in
      the inspection artifact.
- [ ] Add timeouts, budget limits, retry policy and a safe `INSUFFICIENT_EVIDENCE`
      fallback.
- [ ] Keep Devin's code-writing role in a separate development workflow with tests and
      pull requests; production model/policy changes require review and revalidation.

### Phase 4 — real drone integration

- [ ] Select an indoor platform with prop guards, payload margin and a supported
      autopilot SDK.
- [ ] Add redundant positioning suitable for GPS-denied hangars: visual-inertial
      odometry plus depth/LiDAR or another independent source.
- [ ] Implement the onboard safety supervisor and inspection primitive API.
- [ ] Add hardware emergency stop and clearly defined loss-of-link behaviour.
- [ ] Calibrate camera, thermal, microphone and timestamp alignment.
- [ ] Build a controlled test cage and representative component mock-up.
- [ ] Validate electromagnetic compatibility, battery/fire handling and foreign-object
      controls with the site.

### Phase 5 — field validation

- [ ] Create seeded known defects, benign lookalikes and unknown-object scenarios.
- [ ] Run blinded comparisons against qualified inspectors.
- [ ] Demonstrate coverage and defect performance per task, not only overall accuracy.
- [ ] Validate audio with rotors active, quiet hover and landed captures.
- [ ] Exercise people/obstacle entry, sensor failure, network loss and emergency stop.
- [ ] Run shadow inspections in a real hangar and maintain an issue/near-miss log.
- [ ] Freeze a validated hardware/software/model configuration for the pilot.

### Phase 6 — operational and regulatory adoption

- [ ] Map the workflow to the operator/MRO quality system and maintenance records.
- [ ] Establish how the method appears in approved maintenance data or an accepted
      alternative-method process.
- [ ] Document training and competency for operators and inspectors.
- [ ] Establish calibration, maintenance, software/model update and continued
      airworthiness procedures for the inspection system itself.
- [ ] Obtain OEM, customer, competent-authority and insurer agreement appropriate to
      the claimed use.
- [ ] Roll out one approved task/asset/site combination at a time.

## First real-world vertical slice

The first pilot should be intentionally narrow:

- One indoor site.
- One stationary off-wing component family.
- No people inside the controlled flight area.
- Visual and OCR evidence first; thermal and acoustics added after the evidence pipeline
  is stable.
- Drone proposes an identity; a technician confirms it.
- The backend binds a versioned procedure.
- Devin may request close-ups from a fixed list of safe viewpoints.
- A qualified inspector reviews all evidence and makes the disposition.
- AeroLoop measures time, coverage, missed/false findings, aborts and inspector
  disagreement against the existing process.

This slice proves the difficult integration—identity, procedure binding, adaptive
capture, evidence provenance and review—without pretending that general autonomy is
already validated.

## Go/no-go rules

The system must refuse or stop an inspection when:

- The asset cannot be identified and confirmed.
- Applicable maintenance data is missing, stale or does not match the configuration.
- Sensor calibration or time synchronisation is invalid.
- Required evidence cannot meet its quality threshold.
- A person or unmodelled hazard enters the controlled area.
- Position uncertainty or clearance approaches the validated limit.
- Devin/backend connectivity is required for the next step but unavailable.
- Model outputs contradict each other on a safety-relevant finding.
- The hardware, software, model or manual revision differs from the approved baseline.

Stopping with `INSUFFICIENT_EVIDENCE` is a successful safety outcome.

## External standards and evidence to track

The exact compliance route depends on jurisdiction, operator, claimed inspection task
and whether the method is part of approved maintenance data. The implementation team
should maintain a controlled compliance matrix rather than copy regulatory prose into
code.

- EASA Part-145 maintenance-data guidance:
  <https://www.easa.europa.eu/en/the-agency/faqs/part-145>
- EASA Machine Learning Application Approval research, including vision-based
  maintenance inspection:
  <https://www.easa.europa.eu/en/research-projects/machine-learning-application-approval>
- EASA AI Roadmap 2.0:
  <https://www.easa.europa.eu/en/document-library/general-publications/easa-artificial-intelligence-roadmap-20>
- EASA UAS rules and indoor-operation applicability:
  <https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-unmanned-aircraft-systems>
- FAA statement that Part 107 does not apply to indoor-only operation:
  <https://www.faa.gov/faq/do-faa-rules-and-regulations-apply-commercial-uas-or-drone-operations-conducted-indoors-only>
- Devin organisation session API, attachments and structured output:
  <https://docs.devin.ai/api-reference/v3/sessions/post-organizations-sessions>
- Devin structured-output guidance:
  <https://docs.devin.ai/api-reference/v1/structured-output>

These links are starting points, not legal opinions or proof of approval. Before a real
pilot, the MRO/operator's quality, safety, legal and information-security owners should
approve the concept of operations and compliance plan.

