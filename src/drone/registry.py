from typing import List

from drone.api.drone import Drone
from ui.settings.register import register_settings_section_meta
from ui.settings.settings import SettingMetaOptions, SettingMetaString

# Provide the drone connection initializer for each supported drone
drone_classes: List[Drone] = []

# Also register the settings to configure the connection to a drone
register_settings_section_meta("Connection", 0, [
    SettingMetaOptions(None, None, "drone", "The drone model to control",
                       drone_classes[0].get_name() if len(drone_classes) > 0 else "ERR:NoDroneClassRegistered!",
                       [d.get_name() for d in drone_classes]),
    SettingMetaString(None, None, "url", "The URL to connect to. Check the documentation of the drone.",
                      "tcp://192.168.10.1:8889"),
    SettingMetaString(None, None, "extra",
                      "Extra data in json format specific to the drone. Check the documentation of the drone.",
                      "{\"video_url\": \"udp://0.0.0.0:11111\"}"),
])
