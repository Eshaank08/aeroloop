"""The real-world-like mission environment remains deterministic and fail-closed."""

from mission.environment import EnvironmentScenario, GROUND_Z_M, make_environment
from mission.episode import MissionEpisode


def test_environment_is_reproducible_and_labels_synthetic_inputs():
    left = make_environment(606076)
    right = make_environment(606076)

    assert left == right
    sample = left.sample(left.object_start_s + 1.0, (0.0, 0.0, 0.0))
    assert sample["synthetic"] is True
    assert sample["visual_detections"]
    assert sample["visual_detections"][0]["synthetic"] is True
    assert sample["audio"]["synthetic"] is True


def test_frames_expose_wind_and_synthetic_sensor_channels_to_the_replay():
    episode = MissionEpisode(seed=1000, authorised_indexes=[0])
    frame = episode.frames[0]

    assert len(frame["wind"]) == 3
    assert frame["sensors"]["synthetic"] is True
    assert "visual_detections" in frame["sensors"]
    assert "audio" in frame["sensors"]


def test_ground_contact_is_a_verifier_failure():
    episode = MissionEpisode(seed=1000, authorised_indexes=[0])
    episode.drone._position = (0.0, 8.0, GROUND_Z_M - 0.1)
    assert episode._sense_environment() == "ground_contact"

    episode.failure = "ground_contact"
    verification = episode.verify()
    assert verification["passed"] is False
    assert verification["ground_contact"] is True


def test_dynamic_object_inside_the_safety_radius_stops_the_flight():
    episode = MissionEpisode(seed=1000, authorised_indexes=[0])
    episode.environment = EnvironmentScenario(
        seed=1000,
        object_label="bird",
        object_start_s=0.0,
        object_duration_s=10.0,
        object_x_m=0.0,
        object_z_m=6.0,
        object_direction=1,
        audio_peak_s=5.0,
        audio_peak_db=60.0,
    )
    episode.t = 5.0

    assert episode._sense_environment() == "dynamic_obstacle_proximity"
    assert episode.pending_events[-1]["type"] == "dynamic_obstacle_safety_stop"


def test_observation_exposes_current_perception_without_future_schedule():
    episode = MissionEpisode(seed=1000, authorised_indexes=[0])
    packet = episode.observe()

    assert packet.ground_clearance_m > 0
    assert packet.perception["synthetic"] is True
    assert "audio" in packet.perception
