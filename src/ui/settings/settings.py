import abc
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class SettingMeta(abc.ABC):
    """
    Stores metadata about a setting.
    """

    section: Optional[str]
    """The section of the settings page where this setting should be displayed.
    """

    key: Optional[str]
    """The key of the setting.
    """

    title: str
    """The name of the setting.
    """

    desc: str
    """The description of the setting.
    """

    default: any
    """The default value of the setting.
    """


@dataclass
class SettingMetaString(SettingMeta):
    default: str
    type: str = "string"


@dataclass
class SettingMetaNumeric(SettingMeta):
    default: float
    min: float
    max: float
    step: float
    type: str = "numeric"


@dataclass
class SettingMetaOptions(SettingMeta):
    default: str
    options: List[str]
    type: str = "options"
