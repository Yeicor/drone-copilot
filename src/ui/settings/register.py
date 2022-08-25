from typing import List, Tuple

from ui.settings.settings import SettingMeta

_settings_metadata: List[Tuple[str, str, int, List[SettingMeta]]] = []


def register_settings_section_meta(section: str, priority: int, meta: List[SettingMeta], section_id=None):
    """
    :param section: the section title of the setting.
    :param priority: the priority of the setting, lower is higher on the list.
    :param meta: the metadata for the setting.
    :param section_id: the id of the section, defaulting to lowercase `section`.
    """
    section_id = section_id or section.lower()
    for m in meta:
        m.section = section_id
        m.key = m.key or m.title.lower()
    insert_at = binary_search([m[2] for m in _settings_metadata], 0, len(_settings_metadata), priority)
    _settings_metadata.insert(insert_at, (section, section_id, priority, meta))


def binary_search(s: List[any], p: int, q: int, find: any) -> int:
    """
    Binary search. Slightly modified from https://stackoverflow.com/a/27843077.
    :param s: the list to search in.
    :param p: the start index of the search.
    :param q: the end index of the search.
    :param find: the element to look for.
    :return: the index of the element that matches `find`, or the index of the element that is just greater than `find`.
    """
    midpoint = int((p + q) / 2)
    s_midpoint = s[midpoint] if len(s) > midpoint else None
    if find == s_midpoint:
        return midpoint
    elif p == q - 1 or p == q:
        # if find == s[q]:
        return q
    elif find < s_midpoint:
        return binary_search(s, p, midpoint, find)
    elif find > s_midpoint:
        return binary_search(s, midpoint + 1, q, find)
