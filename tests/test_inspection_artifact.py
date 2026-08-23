"""Artifact, approval, and integrity tests for the adaptive evidence loop."""

import json

import pytest

from sim.aircraft_geometry import DEFAULT_NACELLE
from sim.limits import DEFAULT_LIMITS
from inspection.adaptive import AdaptiveRunner
from inspection.artifact import (
    approve_artifact,
    artifact_digest,
    build_artifact,
    check_approval_integrity,
    check_artifact_integrity,
)
from inspection.quality import QualityOracle
from inspection.schema import DISPOSITION_APPROVED


def _artifact(seed: int = 606076):
    runner = AdaptiveRunner(oracle=QualityOracle())
    result = runner.run("test sweep", DEFAULT_NACELLE, DEFAULT_LIMITS, seed=seed, wind_scale=1.0)
    return build_artifact(result, nacelle=DEFAULT_NACELLE, limits=DEFAULT_LIMITS)


def test_artifact_has_synthetic_label():
    artifact = _artifact()
    assert artifact["synthetic"] is True
    for capture in artifact["captures"]:
        assert capture["synthetic"] is True


def test_artifact_digest_includes_timestamp_and_approval():
    artifact = _artifact()
    digest1 = artifact_digest(artifact)
    artifact["generated_at_utc"] = "2099-01-01T00:00:00Z"
    digest2 = artifact_digest(artifact)
    assert digest1 != digest2


def test_approval_covers_exact_timestamp():
    artifact = _artifact()
    artifact["final_disposition"] = "PASS"
    artifact["integrity_digest"] = artifact_digest(artifact)
    approve_artifact(artifact, approver="human-judge")
    assert check_approval_integrity(artifact)
    artifact["generated_at_utc"] = "2099-01-01T00:00:00Z"
    assert not check_approval_integrity(artifact)


def test_same_seed_same_preapproval_content():
    art1 = _artifact(606076)
    art2 = _artifact(606076)
    art1["generated_at_utc"] = art2["generated_at_utc"] = "fixed"
    # Pre-approval contents (digest) should be identical with controlled timestamp.
    assert artifact_digest(art1) == artifact_digest(art2)


def test_mutation_fails_integrity():
    artifact = _artifact()
    assert check_artifact_integrity(artifact)
    artifact["captures"][0]["speed_mps"] = 99.9
    assert not check_artifact_integrity(artifact)


def test_pass_cannot_be_approved_without_human():
    artifact = _artifact()
    with pytest.raises(ValueError):
        approve_artifact(artifact)


def test_approval_and_mutation_fails():
    # Force a passing artifact by overriding disposition.
    artifact = _artifact()
    artifact["final_disposition"] = "PASS"
    # Recompute digest after the override, because we changed the artifact.
    artifact["integrity_digest"] = artifact_digest(artifact)

    approve_artifact(artifact, approver="human-judge")
    assert artifact["approval"]["approved"] is True
    assert artifact["approval"]["approver"] == "human-judge"
    assert check_approval_integrity(artifact)

    # Mutating the artifact after approval invalidates the approval block.
    artifact["captures"][0]["speed_mps"] = 99.9
    assert not check_approval_integrity(artifact)


def test_approval_sets_disposition_approved():
    artifact = _artifact()
    artifact["final_disposition"] = "PASS"
    artifact["integrity_digest"] = artifact_digest(artifact)
    approve_artifact(artifact, approver="human-judge")
    assert artifact["final_disposition"] == DISPOSITION_APPROVED


def test_tampered_preapproval_rejected():
    artifact = _artifact()
    artifact["final_disposition"] = "PASS"
    # integrity_digest still matches the original artifact
    artifact["captures"][0]["speed_mps"] = 999.9
    # the artifact has been tampered with but the digest was not recomputed
    with pytest.raises(ValueError, match="tampered"):
        approve_artifact(artifact, approver="human-judge")
