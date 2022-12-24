import abc
import configparser
from dataclasses import dataclass
from typing import List, Callable

from kivy.app import App
from kivy.clock import Clock


@dataclass
class SettingMeta(abc.ABC):
    """
    Stores metadata about a setting.
    """
    title: str
    """The display name of the setting.
    """

    def key(self) -> str:
        """Returns the key of the setting, generated from the title.
        """
        return self.title.lower().replace(' ', '_')

    def bind(self, section: str, on_change: Callable[[str], None], call_now=True):
        """Binds a callback to changes of the setting's value.
        """

        def handler_wrapper(_app: App, _parser: any, section2: str, key2: str, value: str):
            if section2 == section and key2 == self.key():
                on_change(value)

        App.get_running_app().bind(on_config_change=handler_wrapper)
        if call_now:
            try:
                on_change(App.get_running_app().config.get(section, self.key()))
            except configparser.Error:
                # We asked for the value before the settings were updated, which is technically incorrect
                # Instead, provide the value on the next frame to simplify slightly wrong code
                Clock.schedule_once(lambda _: on_change(App.get_running_app().config.get(section, self.key())))


@dataclass
class SettingMetaTitle(SettingMeta):
    """Stores metadata about a setting that is just a title.
    """
    type: str = "title"

    @staticmethod
    def create(title: str) -> 'SettingMetaTitle':
        return SettingMetaTitle(title)


@dataclass
class SettingMetaString(SettingMeta):
    """Stores metadata about a string setting.
    """
    default: str
    """The default value of the setting.
    """
    desc: str
    """The description of the setting.
    """
    type: str = "string"

    @staticmethod
    def create(title: str, desc: str, default: str) -> 'SettingMetaString':
        return SettingMetaString(title, default, desc)


@dataclass
class SettingMetaNumeric(SettingMeta):
    """Stores metadata about a numeric setting.
    """
    default: str
    """The default value of the setting.
    """
    desc: str
    """The description of the setting.
    """
    type: str = "numeric"

    @staticmethod
    def create(title: str, desc: str, default: any) -> 'SettingMetaNumeric':
        return SettingMetaNumeric(title, default, desc)


@dataclass
class SettingMetaOptions(SettingMeta):
    """Stores metadata about a setting with a list of options from which to choose one.
    """
    options: List[str]
    """The choices for the setting.
    """
    default: str
    """The default value of the setting.
    """
    desc: str
    """The description of the setting.
    """
    type: str = "options"

    @staticmethod
    def create(title: str, desc: str, options: List[str], default: str) -> 'SettingMetaOptions':
        return SettingMetaOptions(title, options, default, desc)
