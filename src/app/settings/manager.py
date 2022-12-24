import dataclasses
import json
from typing import List, Callable

from kivy import Logger
from kivy.app import App

from app.settings.settings import SettingMeta, SettingMetaTitle


class SettingsManager:
    """Controls the configuration of the main app.
    Use mgr[section] to read and modify the setting lists.
    """
    _sections: dict[str, List[SettingMeta]] = {}
    """The raw settings data.
    """
    callbacks: List[Callable[[str, bool], None]] = []
    """The metadata modification callbacks, receiving the modified section, and if it was not deleted.
    """

    @staticmethod
    def instance() -> 'SettingsManager':
        """Returns the singleton instance of the manager.
        """
        return App.get_running_app()  # It should extend this class

    def __getitem__(self, section: str):
        """Returns the list of settings for a section.
        This is READ ONLY, use += to add settings.
        """
        return (self._sections[section] or [])[:]

    def __setitem__(self, section: str, settings: List[SettingMeta]):
        """Fully overwrites the list of settings for a section.
        """
        self._sections[section] = settings
        for c in self.callbacks:
            c(section, True)

    def __delitem__(self, section):
        if section in self._sections:
            del self._sections[section]
            for c in self.callbacks:
                c(section, False)

    def get_defaults(self, target_section: str = None) -> dict[str, dict[str, str]]:
        """Returns a dictionary of the default values of all settings.
        """
        defaults = {}
        for section, settings in self._sections.items():
            if section == target_section:
                defaults[section] = {}
                for setting in settings:
                    if hasattr(setting, 'default'):
                        defaults[section][setting.key()] = setting.default
        return defaults

    def build_sections_json(self) -> dict[str, str]:
        """Builds a JSON representation of the metadata of the settings to load into the App
        """

        def proc(section: str, s: SettingsManager) -> dict:
            key = s.key()
            d = dataclasses.asdict(s)
            if 'default' in d:
                del d['default']
            d['key'] = key
            d['section'] = section
            return d

        return {section: json.dumps([proc(section, setting) for setting in settings])
                for section, settings in self._sections.items()}

    def on_meta_changed(self, app: App, section: str, exists: bool):
        # Populate defaults / read from disk after changes
        if exists:
            for k, v in self.get_defaults(section)[section].items():
                if not app.config.has_section(section):
                    Logger.info(f'SettingsManager: Creating dynamic section {section}')
                    app.config.add_section(section)
                    app.config.read(self.get_application_config())
                if not app.config.has_option(section, k):
                    Logger.info(f'SettingsManager: Setting default for dynamic setting {section}.{k}: {v}')
                    app.config.set(section, k, v)
        else:
            Logger.info(f'SettingsManager: Deleting dynamic section {section}')
            # We do not remove the section to keep hidden settings saved (to recover them later)
            # self.config.remove_section(section)

        # Write the new settings to the configuration file if needed
        app.config.write()


if __name__ == '__main__':
    manager = SettingsManager()
    manager.callbacks += [lambda section: print(f'changed {section}')]
    # Perform some changes that should all print 'changed'
    # noinspection PyDictCreation
    manager['test'] = [SettingMetaTitle.create('test')]
    manager['test'] += [SettingMetaTitle.create('test2')]
    manager['test'].append(SettingMetaTitle.create('test3'))  # Not valid
    manager['test3'] = [SettingMetaTitle.create('test3')]
    #
    print(manager.get_defaults())
    print(manager.build_sections_json())
