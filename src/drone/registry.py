from typing import List, Type, Optional, Callable

from kivy import Logger
from kivy.config import ConfigParser

from app.settings.manager import SettingsManager
from app.settings.settings import SettingMetaOptions, SettingMetaNumeric
from drone.api.drone import Drone
from drone.tello.drone import TelloDrone
from drone.test.drone import TestDrone


class DroneRegistry:
    # Provide the drone connection initializer for each supported drone
    _drone_classes: List[Type[Drone]] = [TestDrone, TelloDrone]
    section_name = 'Connection'

    def setup_settings(self):
        settings = SettingsManager.instance()
        _available_drone_names = [d.get_name() for d in self._drone_classes]
        settings[self.section_name] = [
            SettingMetaOptions.create(
                'Drone', 'The drone model to control', _available_drone_names, _available_drone_names[0]),
            # SettingMetaString.create(
            #     'URL', 'The URL to connect to. Check the documentation of the drone.', 'tcp://192.168.10.1:8889'),
            SettingMetaNumeric.create('Timeout', 'The timeout in seconds to connect to the drone.', 12.0),
        ]

    def drone_connect_auto(self, config: ConfigParser, callback: Callable[[Optional[Drone]], None]):
        """Connects to the drone using the specified app configuration
        """
        # Figure out the drone model to connect to
        drone_class_name = config.get(self.section_name, "drone")
        drone_class = None
        for c in self._drone_classes:
            if c.get_name() == drone_class_name:
                drone_class = c
                break
        if drone_class is None:
            Logger.error(f'No drone class found for name {drone_class_name}')
            return  # Disconnect callback chain on error

        # Perform the connection and register the callback
        drone_class.connect(float(config.get(self.section_name, "timeout")), callback)
