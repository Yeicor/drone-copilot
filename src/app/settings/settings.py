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

    default: str
    """The default value of the setting.
    """


@dataclass
class SettingMetaTitle(SettingMeta):
    type: str = "title"

    @staticmethod
    def create(title: str):
        return SettingMetaTitle(title, '')


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

    @staticmethod
    def create(title: str, desc: str, default: str, section: Optional[str] = None, key: Optional[str] = None):
        return SettingMetaString(title, default, section, key, desc)


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

    @staticmethod
    def create(title: str, desc: str, default: any, section: Optional[str] = None, key: Optional[str] = None):
        return SettingMetaNumeric(title, default, section, key, desc)


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
    """The choices for the setting.
    """
    type: str = "options"

    @staticmethod
    def create(title: str, desc: str, options: List[str], default: str, section: Optional[str] = None,
               key: Optional[str] = None):
        return SettingMetaOptions(title, default, section, key, desc, options)
