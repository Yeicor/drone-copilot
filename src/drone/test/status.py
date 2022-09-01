import sys
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy3 import Geometry, Face3

from drone.api.linearangular import LinearAngular
from drone.api.status import Status


@dataclass
class TestStatus(Status, EventDispatcher):
    # Basic status information
    _battery: float = 1.0
    _signal: float = 1.0
    _temp: float = 273.15 + 20.0
    _position_attitude: LinearAngular = LinearAngular()
    _velocity: LinearAngular = LinearAngular()

    # Virtual scene of the drone, for collision detection and height
    scene_geoms: List[Geometry] = field(default_factory=list)

    def _raycast_scene(self, direction: np.ndarray) -> float:
        """Perform a raycast in the given direction"""
        # Negate Z and swap YZ (convert drone to OpenGL coordinates)
        pos = self._position_attitude.linear
        pos[1], pos[2] = pos[2], -pos[1]
        direction[1], direction[2] = direction[2], -direction[1]
        return ray_mesh_intersection(pos, direction, self.scene_geoms)

    def start_updates(self, *args, **kwargs):
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
        return 0.0 <= self.height <= 0.1

    @property
    def height(self) -> float:
        # Perform raycasting to check if close to the ground
        # dist = self._raycast_scene(np.array([0, -1, 0]))
        return 0.1

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
        # # Check for collisions with the scene (up, left, right, forward, backward)
        # dist_up = self._raycast_scene(np.array([0, 0, -1]))
        # if 0.0 <= dist_up < 0.1:
        #     Logger.warn('TestStatus: collision (up)')
        #     self._velocity.linear[2] = 0.1  # Fall down a little bit
        # dist_forward = self._raycast_scene(np.array([1, 0, 0]))
        # if 0.0 <= dist_forward < 0.1:
        #     Logger.warn('TestStatus: collision (forward)')
        #     self._velocity.linear[0] = 0.1
        # dist_backward = self._raycast_scene(np.array([-1, 0, 0]))
        # if 0.0 <= dist_backward < 0.1:
        #     Logger.warn('TestStatus: collision (backward)')
        #     self._velocity.linear[0] = -0.1
        # dist_left = self._raycast_scene(np.array([0, 1, 0]))
        # if 0.0 <= dist_left < 0.1:
        #     Logger.warn('TestStatus: collision (left)')
        #     self._velocity.linear[1] = 0.1
        # dist_right = self._raycast_scene(np.array([0, -1, 0]))
        # if 0.0 <= dist_right < 0.1:
        #     Logger.warn('TestStatus: collision (right)')
        #     self._velocity.linear[1] = -0.1
        # noinspection PyUnresolvedReferences
        self.dispatch('on_update')

    def on_update(*args, **kwargs):
        pass


def ray_mesh_intersection(ray_near, ray_dir, geoms: List[Geometry]) -> float:
    """A very slow raycasting implementation.
    """
    dist = sys.float_info.max
    for geom in geoms:
        for face in geom.faces:
            if isinstance(face, Face3):
                dist_tmp = ray_triangle_intersection(ray_near, ray_dir, (np.array(geom.vertices[face.a]),
                                                                         np.array(geom.vertices[face.b]),
                                                                         np.array(geom.vertices[face.c])))
                if dist_tmp < dist:
                    dist = dist_tmp
    return dist


def ray_triangle_intersection(ray_near, ray_dir, v123) -> float:
    """Möller–Trumbore intersection algorithm in pure python
    Based on http://en.wikipedia.org/wiki/M%C3%B6ller%E2%80%93Trumbore_intersection_algorithm
    """
    v1, v2, v3 = v123
    eps = 0.000001
    edge1 = v2 - v1
    edge2 = v3 - v1
    pvec = np.cross(ray_dir, edge2)
    det = edge1.dot(pvec)
    if abs(det) < eps:
        return -1.0
    inv_det = 1. / det
    tvec = ray_near - v1
    u = tvec.dot(pvec) * inv_det
    if u < 0. or u > 1.:
        return -1.0
    qvec = np.cross(tvec, edge1)
    v = ray_dir.dot(qvec) * inv_det
    if v < 0. or u + v > 1.:
        return -1.0
    t = edge2.dot(qvec) * inv_det
    if t < eps:
        return -1.0
    return t
