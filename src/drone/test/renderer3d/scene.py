import os
import tarfile

from kivy import Logger
from kivy3 import Scene
from kivy3.loaders import OBJMTLLoader
from kivy3.loaders import objloader

# HACK: load empty.png (if needed) from the current directory instead of the library which does not contain it
objloader.folder = os.path.dirname(os.path.abspath(__file__))


def load_scene() -> Scene:
    """Load the scene from the compressed tarball included with the application.
    The scene should be extremely simple, to make the rendering and collision detection fast:
    use textures to add complexity.

    All used textures are CC0-licensed and modified from the original ones.
    """
    # Extract the obj file
    extract_to = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..', '.cache', 'models')
    if not os.path.exists(extract_to):
        os.makedirs(extract_to)
        with tarfile.open(os.path.join(os.path.dirname(__file__), 'scene.tar.gz'), 'r|*') as tar:
            tar.extractall(path=extract_to)
        Logger.info('renderer3d: Extracted scene to %s', extract_to)
    else:
        Logger.info('renderer3d: Reusing cached extracted scene from %s', extract_to)
    # Load the obj file
    loader = OBJMTLLoader()
    obj_path = os.path.join(os.path.dirname(__file__), os.path.join(extract_to, 'scene.obj'))
    loaded_obj = loader.load(obj_path, os.path.join(extract_to, 'scene.mtl'))
    # Prepare the scene
    scene = Scene()
    # loaded_obj.pos.y = -0.3  # move the ground down a bit
    # loaded_obj.pos.z = -10  # move the ground down a bit
    scene.add(loaded_obj)
    # TODO: people and cars moving around the scene to test advanced autopilot algorithms
    return scene
