"""Helper widgets that represents a part of the app's UI."""
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout


class AppUIRoot(BoxLayout):
    invalidate = NumericProperty(0)


class BottomBar(GridLayout):
    pass


class LeftBar(BoxLayout):
    pass


class RightBar(BoxLayout):
    pass


class TopBar(BoxLayout):
    pass


class RightPanel(BoxLayout):
    pass
