import abc
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class SettingMeta(abc.ABC):
    """
    Stores metadata about a setting.
    """
    title: str
    """The name of the setting.
    """

    default: any
    """The default value of the setting.
    """


@dataclass
class SettingMetaTitle(SettingMeta):
    type: str = "title"

@dataclass
class SettingMetaString(SettingMeta):
    section: Optional[str]
    """The section of the settings page where this setting should be displayed.
    """
    key: Optional[str]
    """The key of the setting.
    """
    desc: str
    """The description of the setting.
    """
    type: str = "string"


@dataclass
class SettingMetaNumeric(SettingMeta):
    section: Optional[str]
    """The section of the settings page where this setting should be displayed.
    """
    key: Optional[str]
    """The key of the setting.
    """
    desc: str
    """The description of the setting.
    """
    type: str = "numeric"


@dataclass
class SettingMetaOptions(SettingMeta):
    section: Optional[str]
    """The section of the settings page where this setting should be displayed.
    """
    key: Optional[str]
    """The key of the setting.
    """
    desc: str
    """The description of the setting.
    """
    options: List[str]
    type: str = "options"
