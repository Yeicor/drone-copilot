import json
from typing import List, Type, Optional, Callable

from kivy import Logger
from kivy.config import ConfigParser

from drone.api.drone import Drone
from drone.tello.drone import TelloDrone
from drone.test.drone import TestDrone
from app.settings.register import register_settings_section_meta
from app.settings.settings import SettingMetaOptions, SettingMetaString, SettingMetaNumeric

# TODO: Add a test drone driver that explores a safe virtual environment

# Provide the drone connection initializer for each supported drone
_drone_classes: List[Type[Drone]] = [TestDrone, TelloDrone]

# Also register the settings to configure the connection to a drone
register_settings_section_meta('Connection', 'Connection (restart required)', 0, [
    SettingMetaOptions(None, None, 'Drone', 'The drone model to control',
                       _drone_classes[0].get_name() if len(_drone_classes) > 0 else 'ERR:NoDroneClassRegistered!',
                       [d.get_name() for d in _drone_classes]),
    SettingMetaString(None, None, 'URL', 'The URL to connect to. Check the documentation of the drone.',
                      'tcp://192.168.10.1:8889'),
    SettingMetaNumeric(None, None, 'Timeout', 'The timeout in seconds to connect to the drone.', 12.0),
    SettingMetaString(None, None, 'Extra',
                      'Extra data in json format specific to the drone. Check the documentation of the drone.',
                      '{"video_url": "udp://0.0.0.0:11111"}'),
], 'connection')


def drone_connect_auto(config: ConfigParser, callback: Callable[[Optional[Drone]], None]):
    """Connects to the drone using the specified app configuration
    """
    # Figure out the drone model to connect to
    drone_class_name = config.get("connection", "drone")
    drone_class = None
    for c in _drone_classes:
        if c.get_name() == drone_class_name:
            drone_class = c
            break
    if drone_class is None:
        Logger.error(f'No drone class found for name {drone_class_name}')
        return  # Disconnect callback chain on error

    # Perform the connection and register the callback
    drone_class.connect(config.get("connection", "url"), float(config.get("connection", "timeout")),
                        json.loads(config.get("connection", "extra")), callback)
