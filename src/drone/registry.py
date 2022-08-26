import json
from typing import List, Type, Optional, Callable

from kivy.config import ConfigParser

from drone.api.drone import Drone
from drone.tello.drone import TelloDrone
from ui.settings.register import register_settings_section_meta
from ui.settings.settings import SettingMetaOptions, SettingMetaString, SettingMetaNumeric

# Provide the drone connection initializer for each supported drone
_drone_classes: List[Type[Drone]] = [TelloDrone]

# Also register the settings to configure the connection to a drone
register_settings_section_meta('Connection', 0, [
    SettingMetaOptions(None, None, 'drone', 'The drone model to control',
                       _drone_classes[0].get_name() if len(_drone_classes) > 0 else 'ERR:NoDroneClassRegistered!',
                       [d.get_name() for d in _drone_classes]),
    SettingMetaString(None, None, 'url', 'The URL to connect to. Check the documentation of the drone.',
                      'tcp://192.168.10.1:8889'),
    SettingMetaNumeric(None, None, 'timeout', 'The timeout in seconds to connect to the drone.', 12.0),
    SettingMetaString(None, None, 'extra',
                      'Extra data in json format specific to the drone. Check the documentation of the drone.',
                      '{"video_url": "udp://0.0.0.0:11111"}'),
])


def drone_connect_auto(config: ConfigParser, callback: Callable[[Optional[Type[Drone]]], None]):
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
        raise ValueError(f'No drone class found for name {drone_class_name}')

    # Perform the connection and register the callback
    drone_class.connect(config.get("connection", "url"), float(config.get("connection", "timeout")),
                        json.loads(config.get("connection", "extra")), callback)
