import os
import tarfile
from shutil import rmtree

from kivy import Logger
from kivy3 import Scene
from kivy3.loaders import OBJMTLLoader
from kivy3.loaders import objloader

from util.filesystem import source, cache

# HACK: load empty.png (if needed) from the current directory instead of the library which does not contain it
objloader.folder = source('drone', 'test', 'renderer3d')


def load_scene() -> Scene:
    """Load the scene from the compressed tarball included with the application.
    The scene should be extremely simple, to make the rendering and collision detection fast:
    use textures to add complexity.

    All used textures are CC0-licensed and modified from the original ones.
    """
    # Extract the obj file
    extract_to = cache('scene')
    with tarfile.open(source('drone', 'test', 'renderer3d', 'scene.tar.gz'), 'r|*') as tar:
        tar.extractall(path=extract_to)
    Logger.info('renderer3d: Extracted scene to %s', extract_to)
    # Load the obj file
    loader = OBJMTLLoader()
    loaded_obj = loader.load(os.path.join(extract_to, 'scene.obj'), os.path.join(extract_to, 'scene.mtl'))
    rmtree(extract_to)  # Cleanup the temporary directory (no files left on the device)
    # Prepare the scene
    scene = Scene()
    # loaded_obj.pos.y = -0.3  # move the ground down a bit
    # loaded_obj.pos.z = -10  # move the ground down a bit
    scene.add(loaded_obj)
    # TODO: people and cars moving around the scene to test advanced autopilot algorithms
    return scene
