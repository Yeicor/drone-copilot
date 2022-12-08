import math
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from kivy import Logger
from kivy.clock import Clock
from kivy.event import EventDispatcher

from drone.api.linearangular import LinearAngular
from drone.api.status import Status
from drone.test.camera import TestCamera

_DRONE_LAND_HEIGHT = 0.05
_DRONE_COLLISION_RADIUS = 0.2


@dataclass
class TestStatus(Status, EventDispatcher):
    # The camera contains the virtual scene for collision detection and height calculation
    camera: TestCamera

    # Basic status information (using units of the drone API)
    _battery: float = 1.0
    _signal: float = 1.0
    _temp: float = 273.15 + 20.0
    _position_attitude: LinearAngular = LinearAngular(angular=np.array([0, 0, math.pi]))
    _velocity: LinearAngular = LinearAngular()

    def start_updates(self):
        # noinspection PyUnresolvedReferences
        self.register_event_type('on_update')
        # noinspection PyUnresolvedReferences
        self.register_event_type('on_collision')
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
        return self.height > _DRONE_LAND_HEIGHT or self.height < 0.0

    @property
    def height(self) -> float:
        return self.camera.raycast(self._position_attitude.linear_local, np.array([0, 0, 1]))

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
        speed_linear_abs = self.velocity.linear_abs(self.position_attitude.angular)
        speed_angular = self.velocity.angular
        self._position_attitude.linear_local += speed_linear_abs * dt
        self._position_attitude.angular += speed_angular * dt
        # FIXME: Check for collisions with the scene
        self._collision_check([0, 0, 1], landing=True)  # Down (assume safe landing)
        self._collision_check([0, 0, -1])  # Up
        self._collision_check([0, 1, 0])  # Left
        self._collision_check([0, -1, 0])  # Right
        self._collision_check([1, 0, 0])  # Forward
        self._collision_check([-1, 0, 0])  # Backward
        # noinspection PyUnresolvedReferences
        self.dispatch('on_update')

    def _collision_check(self, ray_dir: List[float], landing=False):
        # Check if move direction is aligned with collision test direction
        may_collide = self.velocity.linear_abs(self.position_attitude.angular).dot(ray_dir) > 0.0
        if may_collide:
            # NOTE: You can force yourself through an obstacle by repeatedly going forward and stopping.
            dist = self.camera.raycast(self.position_attitude.linear_local, np.array(ray_dir))
            if 0.0 <= dist < _DRONE_COLLISION_RADIUS:
                # noinspection PyUnresolvedReferences
                self.dispatch('on_collision', ray_dir, dist)
                if not landing:
                    self._velocity.linear_local = -np.array(ray_dir) * 0.25  # Bounce a little bit
                    self._velocity.angular = np.zeros(3)  # Stop rotation

                    def reset_vel(_dt: float):
                        self._velocity.linear_local = np.zeros(3)

                    Clock.schedule_once(reset_vel, 0.1)
                else:
                    if dist < _DRONE_LAND_HEIGHT:  # When landing go lower and just stop moving
                        self._velocity.linear_local = np.zeros(3)
                        self._velocity.angular = np.zeros(3)

    def on_update(self):
        pass

    # noinspection PyMethodMayBeStatic
    def on_collision(self, ray_dir, dist):
        Logger.warn('TestStatus: collision (ray_dir: %s, dist: %.3fm)', ray_dir, dist)
