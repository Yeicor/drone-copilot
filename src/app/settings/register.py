from typing import List, Tuple, Dict

from app.settings.settings import SettingMeta, SettingMetaTitle

_settings_metadata: Dict[str, List[Tuple[str, str, int, List[SettingMeta]]]] = {}


def register_settings_section_meta(title: str, section: str, priority: int, meta: List[SettingMeta], section_id=None):
    """
    :param title: the title of the settings section.
    :param section: the subsection title.
    :param priority: the priority of the setting, lower is higher on the list.
    :param meta: the metadata for the setting.
    :param section_id: the id of the section, defaulting to lowercase `section`.
    """
    if title not in _settings_metadata:
        _settings_metadata[title] = []
    # Insert the section into the list of sections for the given title.
    section_id = section_id or section.lower()
    for m in meta:
        m.section = section_id
        m.key = m.key or m.title.lower()
    insert_at = binary_search([m[2] for m in _settings_metadata[title]], 0, len(_settings_metadata[title]), priority)
    print(f"Inserting {section} at {insert_at}, length is {len(_settings_metadata[title])}")
    meta = [SettingMetaTitle(section, section_id)] + meta  # Prepend the section title.
    _settings_metadata[title].insert(insert_at, (section, section_id, priority, meta))
    print("Length is now", len(_settings_metadata[title]))
    print(_settings_metadata[title])


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
