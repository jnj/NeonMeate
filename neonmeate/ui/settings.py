from gi.repository import Gtk


# noinspection PyUnresolvedReferences,PyArgumentList
class SettingsMenu(Gtk.Popover):
    def __init__(self):
        super(SettingsMenu, self).__init__()
        self._vbox = Gtk.VBox()
        self._host_entry = Gtk.Entry()
        self._port_entry = Gtk.Entry()
        self._host_entry.set_text('localhost')
        self._port_entry.set_text('6600')
        self._vbox.pack_start(self._host_entry, True, True, 0)
        self._vbox.pack_start(self._port_entry, True, True, 0)
        self.add(self._vbox)
        self._vbox.show_all()