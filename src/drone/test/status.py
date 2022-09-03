from dataclasses import dataclass
from typing import Dict

import numpy as np
from kivy import Logger
from kivy.clock import Clock
from kivy.event import EventDispatcher

from drone.api.linearangular import LinearAngular
from drone.api.status import Status
from drone.test.camera import TestCamera


@dataclass
class TestStatus(Status, EventDispatcher):
    # The camera contains the virtual scene for collision detection and height calculation
    camera: TestCamera

    # Basic status information
    _battery: float = 1.0
    _signal: float = 1.0
    _temp: float = 273.15 + 20.0
    _position_attitude: LinearAngular = LinearAngular()
    _velocity: LinearAngular = LinearAngular()

    def start_updates(self):
        # noinspection PyUnresolvedReferences
        self.register_event_type('on_update')
        # Run update() every frame to update the transform, check for collisions and run callbacks.
        Clock.schedule_interval(self.update, 0.0)

    @property
    def battery(self) -> float:
        return self._battery

    @property
    def signal_strength(self) -> float:
        return self._signal

    @property
    def temperatures(self) -> Dict[str, float]:
        return {"temp": self._temp}

    @property
    def flying(self) -> bool:
        # Perform raycasting to check if close to the ground
        return 0.0 <= self.height <= 0.1

    @property
    def height(self) -> float:
        return self.camera.raycast(self._position_attitude.linear, np.array([0, -1, 0]))

    @property
    def position_attitude(self) -> LinearAngular:
        return self._position_attitude

    @property
    def velocity(self) -> LinearAngular:
        return self._velocity

    @property
    def acceleration(self) -> LinearAngular:
        return LinearAngular()  # Unknown!

    def update(self, dt: float):
        """Run this on every frame to update the position and check for collisions.
        You should also notify any status update listeners.
        """
        # Update the position and attitude
        self._position_attitude.linear += self._velocity.linear * dt
        self._position_attitude.angular += self._velocity.angular * dt
        # Check for collisions with the scene (up, left, right, forward, backward)
        dist_up = self.camera.raycast(self._position_attitude.linear, np.array([0, 0, -1]))
        if 0.0 <= dist_up < 0.1:
            Logger.warn('TestStatus: collision (up)')
            self._velocity.linear[2] = 0.1  # Fall down a little bit
        dist_forward = self.camera.raycast(self._position_attitude.linear, np.array([1, 0, 0]))
        if 0.0 <= dist_forward < 0.1:
            Logger.warn('TestStatus: collision (forward)')
            self._velocity.linear[0] = 0.1
        dist_backward = self.camera.raycast(self._position_attitude.linear, np.array([-1, 0, 0]))
        if 0.0 <= dist_backward < 0.1:
            Logger.warn('TestStatus: collision (backward)')
            self._velocity.linear[0] = -0.1
        dist_left = self.camera.raycast(self._position_attitude.linear, np.array([0, 1, 0]))
        if 0.0 <= dist_left < 0.1:
            Logger.warn('TestStatus: collision (left)')
            self._velocity.linear[1] = 0.1
        dist_right = self.camera.raycast(self._position_attitude.linear, np.array([0, -1, 0]))
        if 0.0 <= dist_right < 0.1:
            Logger.warn('TestStatus: collision (right)')
            self._velocity.linear[1] = -0.1
        # noinspection PyUnresolvedReferences
        self.dispatch('on_update')

    def on_update(*args, **kwargs):
        pass
