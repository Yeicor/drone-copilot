import dataclasses
import json
from typing import Dict

if True:  # List of imports that automatically register settings:
    from drone.registry import Drone
    from app.ui.appui import AppUI

    _ = Drone
    _ = AppUI


# noinspection PyTypeChecker
def get_settings_meta() -> {str: str}:
    """
    :return: the complete list of settings metadata. Intended for the main app.
    """
    from app.settings.register import _settings_metadata
    # Build the metadata.
    dict_of_lists = {title: [{"type": "title", "title": section[0]}] + [dataclasses.asdict(x) for x in section[3]]
                     for title, sections in _settings_metadata.items() for section in sections}
    # Remove default values from the copied metadata dictionary.
    for title, sections in dict_of_lists.items():
        for section in sections:
            if "default" in section:
                del section["default"]
    # Serialize the dictionary of lists to a JSON string.
    meta_dict = {title: json.dumps(sublist) for title, sublist in dict_of_lists.items()}
    return meta_dict


def get_settings_defaults() -> Dict[str, Dict[str, any]]:
    """
    :return: the default values for all settings groups. Intended for the main app.
    """
    from app.settings.register import _settings_metadata
    return {v[1]: {v2.key: v2.default for v2 in v[3]} for title, m in _settings_metadata.items() for v in m}
