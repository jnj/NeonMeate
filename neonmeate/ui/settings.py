from gi.repository import Gtk, GObject

from ..util.config import main_config_file


class SettingsMenu(Gtk.Popover):
    SIG_CONNECT_ATTEMPT = 'neonmeate-connect-attempt'
    SIG_MUSIC_DIR_UPDATED = 'neonmeate-musicdir-updated'
    SIG_UPDATE_REQUESTED = 'neonmeate-update-requested'

    __gsignals__ = {
        SIG_CONNECT_ATTEMPT :
            (GObject.SignalFlags.RUN_FIRST, None, (str, int, bool,)),
        SIG_MUSIC_DIR_UPDATED : (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        SIG_UPDATE_REQUESTED : (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, executor, configstate, connstatus, cfg):
        super(SettingsMenu, self).__init__()
        self._exec = executor
        self._cfg = cfg
        self._configstate = configstate
        self._connstatus = connstatus
        self._connstatus.connect('mpd_connected', self._on_mpd_connection)
        spacing = 10
        self.set_border_width(spacing)
        self._grid = Gtk.Grid()
        self._grid.set_column_spacing(spacing)
        self._grid.set_row_spacing(spacing)
        self.add(self._grid)

        host_label = Gtk.Label('Host')
        host_label.set_xalign(0)
        host_label.set_justify(Gtk.Justification.LEFT)
        self._grid.add(host_label)
        host, port = self._configstate.get_host_and_port()
        self._host_entry = Gtk.Entry()
        self._host_entry.set_input_purpose(Gtk.InputPurpose.ALPHA)
        self._host_entry.set_text(host)
        self._grid.add(self._host_entry)

        port_label = Gtk.Label('Port')
        port_label.set_xalign(0)
        port_label.set_justify(Gtk.Justification.LEFT)
        self._grid.attach_next_to(port_label, host_label,
                                  Gtk.PositionType.BOTTOM, 1, 1)

        self._port_entry = Gtk.Entry()
        self._port_entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
        self._port_entry.set_text(str(port))
        self._grid.attach_next_to(self._port_entry, port_label,
                                  Gtk.PositionType.RIGHT, 1, 1)

        music_dir_label = Gtk.Label('Music Folder')
        music_dir_label.set_xalign(0)
        music_dir_label.set_justify(Gtk.Justification.LEFT)
        music_dir_chooser = Gtk.FileChooserButton()
        music_dir_chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        music_dir_chooser.set_local_only(True)
        music_dir_chooser.set_current_folder(self._configstate.get_musicpath())
        music_dir_chooser.connect('file-set', self._on_music_folder)

        self._grid.attach_next_to(music_dir_label, port_label,
                                  Gtk.PositionType.BOTTOM, 1, 1)
        self._grid.attach_next_to(music_dir_chooser, music_dir_label,
                                  Gtk.PositionType.RIGHT, 1, 1)

        self._connect_label = Gtk.Label('Connect')
        self._connect_label.set_xalign(0)
        self._connect_label.set_justify(Gtk.Justification.LEFT)
        self._grid.attach_next_to(self._connect_label, music_dir_label,
                                  Gtk.PositionType.BOTTOM, 1, 1)
        switch_box = Gtk.Box()
        self._connect_switch = Gtk.Switch()
        switch_box.pack_end(self._connect_switch, False, False, 0)
        self._grid.attach_next_to(switch_box, self._connect_label,
                                  Gtk.PositionType.RIGHT, 1, 1)
        self._connect_switch.connect('notify::active',
                                     self._on_user_connect_change)

        self._update_btn = Gtk.Button(label='Update')
        self._update_btn.set_can_focus(False)
        self._update_btn.set_tooltip_text('Update the database')
        self._update_btn.connect('clicked', self._on_update_request)
        self._grid.attach_next_to(self._update_btn, switch_box,
                                  Gtk.PositionType.BOTTOM, 1, 1)

        self._save_btn = Gtk.Button(label='Save')
        self._save_btn.set_can_focus(False)
        self._save_btn.connect('clicked', self._on_save_settings)
        self._grid.attach_next_to(self._save_btn, self._update_btn,
                                  Gtk.PositionType.BOTTOM, 1, 1)

        self._clear_colors_btn = Gtk.Button(label='Clear Cache')
        self._clear_colors_btn.set_can_focus(False)
        self._clear_colors_btn.connect('clicked', self._on_clear_colors)
        self._grid.attach_next_to(self._clear_colors_btn, self._save_btn,
                                  Gtk.PositionType.BOTTOM, 1, 1)
        self._grid.show_all()

    def _on_clear_colors(self, btn):
        self._cfg.clear_background_cache()
        self._save()

    def _on_mpd_connection(self, _, success):
        self._connect_switch.set_active(success)
        txt = 'Connected' if success else 'Connect'
        self._connect_label.set_text(txt)

    def _on_update_request(self, btn):
        self.emit(SettingsMenu.SIG_UPDATE_REQUESTED)

    def _on_save_settings(self, btn):
        self._save()

    def _save(self):
        self._cfg.save(main_config_file())

    def _on_music_folder(self, chooser):
        current = self._configstate.get_musicpath()
        chosen = chooser.get_filename()
        self._cfg.set_music_dir(chosen)
        self._save()
        if current != chosen:
            self._configstate.set_musicpath(chosen)
            self.emit(SettingsMenu.SIG_MUSIC_DIR_UPDATED, chosen)

    def _on_user_connect_change(self, switch, gparam):
        connected = switch.get_active()
        self._host_entry.set_editable(not connected)
        self._port_entry.set_editable(not connected)
        host = self._host_entry.get_text()
        port = int(self._port_entry.get_text())
        self._configstate.set_host_and_port(host, port)
        self.emit('neonmeate-connect-attempt', host, port, connected)
        label_txt = 'Connected' if connected else 'Connect'
        self._connect_label.set_text(label_txt)
