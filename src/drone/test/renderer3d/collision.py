import sys

import numpy as np
from kivy3 import Scene, Object3D, Mesh, Face3, Geometry


def raycast_scene(ray_near: np.ndarray, ray_dir: np.ndarray, scene: Scene) -> float:
    """A very slow raycasting implementation. TODO: Use an optimized implementation

    Remember that this uses the OpenGL coordinate system.
    """
    dist = sys.float_info.max
    to_process = [scene]
    while to_process:
        obj = to_process.pop()
        if isinstance(obj, Object3D):
            to_process.extend(obj.children)
        if isinstance(obj, Mesh) and isinstance(obj.geometry, Geometry):
            geom = obj.geometry
            for face in geom.faces:
                if isinstance(face, Face3):
                    dist_tmp = ray_triangle_intersection(ray_near, ray_dir, (np.array(geom.vertices[face.a]),
                                                                             np.array(geom.vertices[face.b]),
                                                                             np.array(geom.vertices[face.c])))
                    if dist_tmp < dist:
                        dist = dist_tmp
    if dist == sys.float_info.max:
        dist = -1.0  # No collision
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
