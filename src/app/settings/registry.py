import dataclasses
import json
from typing import Dict

import numpy as np
from kivy import Logger


# noinspection PyTypeChecker
def get_settings_meta() -> {str: str}:
    """
    :return: the complete list of settings metadata. Intended for the main app.
    """
    from app.settings.register import _settings_metadata
    # Build the metadata.
    dict_of_lists = {title + '___' + str(i): [dataclasses.asdict(x) for x in section[3]]
                     for title, sections in _settings_metadata.items() for i, section in enumerate(sections)}
    # Flatten by title while merging values
    dict_of_lists = {k.split('___')[0]: list(
        np.array([v2 for k2, v2 in dict_of_lists.items() if k2.startswith(k.split('___')[0])]).flatten())
        for k, v in dict_of_lists.items()}
    # Remove default values from the copied metadata dictionary.
    for title, sections in dict_of_lists.items():
        for section in sections:
            if "default" in section:
                del section["default"]
            if "on_change" in section:
                del section["on_change"]
    # Serialize the dictionary of lists to a JSON string.
    meta_dict = {title: json.dumps(sublist) for title, sublist in dict_of_lists.items()}
    return meta_dict


def get_settings_defaults() -> Dict[str, Dict[str, any]]:
    """
    :return: the default values for all settings groups. Intended for the main app.
    """
    from app.settings.register import _settings_metadata
    # Build the metadata.
    dict_of_dicts = {section[1] + '___' + str(i): {v2.key: v2.default for v2 in section[3] if hasattr(v2, 'key')} for
                     title, sections in _settings_metadata.items() for i, section in enumerate(sections)}
    # print(dict_of_dicts)
    # Flatten by title while merging values
    dict_of_dicts = {k.split('___')[0]: {k3: v3 for d in
                                         [v2 for k2, v2 in dict_of_dicts.items() if k2.startswith(k.split('___')[0])]
                                         for k3, v3 in d.items()}
                     for k, v in dict_of_dicts.items()}
    # print(dict_of_dicts)
    return dict_of_dicts


def handle_settings_change(section: str, key: str, value: str):
    """
    Handle a settings change.
    :param section: the section of the setting.
    :param key: the key of the setting.
    :param value: the new value of the setting.
    """
    from app.settings.register import _settings_metadata
    # Find the setting.
    found = False
    for title, sections in _settings_metadata.items():
        for section2, section_id, priority, meta in sections:
            for m in meta:
                if getattr(m, 'section', None) == section and getattr(m, 'key', None) == key:
                    found = True
                    # Call the on_change function.
                    if getattr(m, 'on_change', None) is not None:
                        m.on_change(value)
                    else:
                        Logger.warn("handle_settings_change: no on_change function for setting: " + str(m))
    if not found:
        Logger.error("handle_settings_change: BUG: no setting found for section: " + section + ", key: " + key)
