from ui.settings.register import register_settings_section_meta
from ui.settings.settings import SettingMetaNumeric

register_settings_section_meta('UI', 1000, [
    SettingMetaNumeric(None, None, 'Scaling', 'The scale multiplier of the UI elements', 1.0),
    SettingMetaNumeric(None, None, 'Opacity', 'The opacity multiplier of the UI elements', 1.0)
])
