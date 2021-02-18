from gi.repository import Gtk, GObject


# noinspection PyUnresolvedReferences,PyArgumentList
class SettingsMenu(Gtk.Popover):
    __gsignals__ = {
        'neonmeate-mpd-connect': (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        'neonmeate-musicdir-updated': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super(SettingsMenu, self).__init__()
        spacing = 10
        self.set_border_width(spacing)
        self._grid = Gtk.Grid()
        self._grid.set_column_spacing(spacing)
        self._grid.set_row_spacing(spacing)
        self.add(self._grid)

        host_label = Gtk.Label('Host')
        host_label.set_justify(Gtk.Justification.LEFT)
        self._grid.add(host_label)

        self._host_entry = Gtk.Entry()
        self._host_entry.set_text('localhost')
        self._grid.add(self._host_entry)

        port_label = Gtk.Label('Port')
        port_label.set_justify(Gtk.Justification.LEFT)
        self._grid.attach_next_to(port_label, host_label,
                                  Gtk.PositionType.BOTTOM, 1, 1)

        self._port_entry = Gtk.Entry()
        self._port_entry.set_text('6600')
        self._grid.attach_next_to(self._port_entry, port_label,
                                  Gtk.PositionType.RIGHT, 1, 1)

        self._connect_label = Gtk.Label('Connect')
        self._connect_label.set_justify(Gtk.Justification.LEFT)
        self._grid.attach_next_to(self._connect_label, port_label,
                                  Gtk.PositionType.BOTTOM, 1, 1)
        switch_box = Gtk.Box()
        connect_switch = Gtk.Switch()
        switch_box.pack_end(connect_switch, False, False, 0)
        self._grid.attach_next_to(switch_box, self._connect_label,
                                  Gtk.PositionType.RIGHT, 1, 1)
        connect_switch.connect('notify::active', self._on_connect_change)
        music_dir_label = Gtk.Label('Music Folder')
        music_dir_label.set_justify(Gtk.Justification.LEFT)
        music_dir_chooser = Gtk.FileChooserButton()
        music_dir_chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        music_dir_chooser.set_local_only(True)
        music_dir_chooser.connect('file-set', self._on_music_folder)

        self._grid.attach_next_to(music_dir_label, self._connect_label,
                                  Gtk.PositionType.BOTTOM, 1, 1)
        self._grid.attach_next_to(music_dir_chooser, music_dir_label,
                                  Gtk.PositionType.RIGHT, 1, 1)
        self._grid.show_all()

    def _on_music_folder(self, chooser):
        print(f'file chosen {chooser.get_filename()}')

    def _on_connect_change(self, switch, gparam):
        connected = switch.get_active()
        self._host_entry.set_editable(not connected)
        self._port_entry.set_editable(not connected)
        self.emit('neonmeate-mpd-connect', connected)
        label_txt = 'Connected' if connected else 'Connect'
        self._connect_label.set_text(label_txt)
