"""Flight controller for autonomous jet engine nacelle inspection.

THIS FILE IS DEVIN'S JOB. It currently does nothing and fails the verifier by design.

Read README.md for the full task spec, the interface contract, and the pass thresholds.
Run `pytest -q` to see where you stand.
"""


class Controller:
    def __init__(self, waypoints, nacelle, limits):
        self.waypoints = waypoints
        self.nacelle = nacelle
        self.limits = limits

    def step(self, t, position, velocity):
        """Return the desired acceleration (ax, ay, az) for this tick.

        The stub hovers in place, so it visits no waypoints and fails on coverage.
        """
        return (0.0, 0.0, 0.0)
