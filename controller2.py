"""Bare hover controller stub for simulator v2."""


class Controller:
    def __init__(self, waypoints, nacelle, params):
        self.params = params

    def step(self, t, state):
        return (
            self.params.mass * self.params.gravity,
            0.0,
            0.0,
            0.0,
        )
