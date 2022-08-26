import dataclasses
import json
from typing import Dict

from .register import _settings_metadata

if True:
    # List of imports that automatically register settings:
    from drone.registry import _drone_classes

    _ = _drone_classes


# noinspection PyTypeChecker
def get_settings_meta() -> str:
    """
    :return: the complete list of settings metadata. Intended for the main app.
    """
    list_of_lists = [[{"type": "title", "title": m[0]}] + [dataclasses.asdict(x) for x in m[3]]
                     for m in _settings_metadata]
    meta_list = [el for sublist in list_of_lists for el in sublist]
    for el in meta_list:
        if 'default' in el:
            del el['default']
    return json.dumps(meta_list)


def get_settings_defaults() -> Dict[str, Dict[str, any]]:
    """
    :return: the default values for all settings groups. Intended for the main app.
    """
    return {m[1]: {m.key: m.default for m in m[3]} for m in _settings_metadata}
