from gi.repository import Gtk, GObject

from ..util.config import main_config_file


def left_label(txt):
    lbl = Gtk.Label(txt)
    lbl.set_xalign(0)
    lbl.set_justify(Gtk.Justification.LEFT)
    return lbl


class SettingsGrid(Gtk.Grid):
    def __init__(self):
        super(SettingsGrid, self).__init__()
        spacing = 10
        self.set_column_spacing(spacing)
        self.set_row_spacing(spacing)
        self.set_property('margin', spacing)

    def _attach(self, to_attach, attached, pos_type):
        self.attach_next_to(to_attach, attached, pos_type, 1, 1)

    def attach_right(self, to_attach, left_item):
        self._attach(to_attach, left_item, Gtk.PositionType.RIGHT)

    def attach_under(self, to_attach, top_item):
        self._attach(to_attach, top_item, Gtk.PositionType.BOTTOM)


class NetworkSettings(SettingsGrid):

    def __init__(self, configstate):
        super(NetworkSettings, self).__init__()
        host_label = left_label('Host')
        self.add(host_label)
        host, port = configstate.get_host_and_port()
        self._host_entry = host_entry = Gtk.Entry()
        host_entry.set_input_purpose(Gtk.InputPurpose.ALPHA)
        host_entry.set_text(host)
        self.add(host_entry)

        port_label = left_label('Port')
        self.attach_under(port_label, host_label)
        self._port_entry = port_entry = Gtk.Entry()
        port_entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
        port_entry.set_text(str(port))
        self.attach_right(port_entry, port_label)

        passwd_label = left_label('Password')
        self.attach_under(passwd_label, port_label)
        self._passwd_entry = passwd_entry = Gtk.Entry()
        passwd_entry.set_visibility(False)
        passwd_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.attach_right(passwd_entry, passwd_label)
        self.show_all()

    def get_host_setting(self):
        return self._host_entry.get_text()

    def get_port_setting(self):
        return int(self._port_entry.get_text())

    def get_password_setting(self):
        return self._passwd_entry.get_text()

    def on_connected(self, connected):
        self._update_entry_editability(connected)

    def on_user_connect_change(self, connected):
        self._update_entry_editability(connected)

    def _update_entry_editability(self, connected):
        for entry in [self._host_entry, self._port_entry, self._passwd_entry]:
            entry.set_property('editable', not connected)
            entry.set_can_focus(not connected)


class LibrarySettings(SettingsGrid):
    SIG_MUSIC_DIR_UPDATED = 'neonmeate-musicdir-updated'
    SIG_UPDATE_REQUESTED = 'neonmeate-update-requested'
    SIG_CACHE_CLEARED = 'neonmeate-cache-cleared'

    __gsignals__ = {
        SIG_MUSIC_DIR_UPDATED: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        SIG_UPDATE_REQUESTED: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIG_CACHE_CLEARED: (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, configstate, cfg):
        super(LibrarySettings, self).__init__()
        self._configstate = configstate
        self._cfg = cfg
        music_dir_label = left_label('Music Folder')
        music_dir_chooser = Gtk.FileChooserButton()
        music_dir_chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        music_dir_chooser.set_local_only(True)
        music_dir_chooser.set_current_folder(configstate.get_musicpath())
        music_dir_chooser.connect('file-set', self._on_music_folder)

        self.add(music_dir_label)
        self.attach_right(music_dir_chooser, music_dir_label)
        albums_view_label = left_label('Artists')
        self.attach_under(albums_view_label, music_dir_label)

        self._include_comps_box = Gtk.ComboBoxText()
        self._include_comps_box.append('0', 'All')
        self._include_comps_box.append('1', 'Only album artists')
        include_comps = cfg.get_albums_include_comps()
        self._include_comps_box.set_active(0 if include_comps else 1)
        self.attach_right(self._include_comps_box, albums_view_label)
        self._include_comps_box.connect('changed', self._on_album_view_change)

        db_label = left_label('Database')
        self.attach_under(db_label, albums_view_label)
        self._update_btn = Gtk.Button(label='Update')
        self._update_btn.set_can_focus(False)
        self._update_btn.set_tooltip_text('Update the database')
        self._update_btn.connect('clicked', self._on_update_request)
        self.attach_right(self._update_btn, db_label)

        cache_label = left_label('Color cache')
        self.attach_under(cache_label, db_label)
        self._clear_btn = Gtk.Button(label='Clear')
        self._clear_btn.set_can_focus(False)
        self._clear_btn.connect('clicked', self._on_clear_colors)
        self.attach_right(self._clear_btn, cache_label)
        self.show_all()

    def _on_clear_colors(self, btn):
        self._cfg.clear_background_cache()
        self.emit(LibrarySettings.SIG_CACHE_CLEARED)

    def _on_update_request(self, btn):
        self.emit(LibrarySettings.SIG_UPDATE_REQUESTED)

    def _on_album_view_change(self, widget):
        active = self._include_comps_box.get_active()
        include_comps = active == 0
        self._cfg.set_albums_include_comps(include_comps)
        self._configstate.set_albums_include_comps(include_comps)

    def _on_music_folder(self, chooser):
        current = self._configstate.get_musicpath()
        chosen = chooser.get_filename()
        self._cfg.set_music_dir(chosen)
        if current != chosen:
            self._configstate.set_musicpath(chosen)
            self.emit(SettingsMenu.SIG_MUSIC_DIR_UPDATED, chosen)


class OutputsSettings(SettingsGrid):
    SIG_OUTPUT_CHANGE = 'neonmeate-output-change'

    __gsignals__ = {
        SIG_OUTPUT_CHANGE: (GObject.SignalFlags.RUN_FIRST, None, (int, bool,))
    }

    def __init__(self):
        super(OutputsSettings, self).__init__()
        self.set_column_spacing(30)
        self._outputs = []
        self._update()

    def on_outputs(self, outputs):
        self._outputs.clear()
        self._outputs.extend(outputs)
        self._update()
        self.queue_draw()

    def _on_user_toggle(self, switch, gparam, name, id):
        enabled = switch.get_active()
        self.emit(OutputsSettings.SIG_OUTPUT_CHANGE, int(id), enabled)

    def _connect_switch(self, switch, output_id, output_name):
        switch.connect(
            'notify::active',
            self._on_user_toggle,
            output_name,
            output_id
        )

    def _update(self):
        for c in self.get_children():
            self.remove(c)
        prev = None

        for output in self._outputs:
            box = Gtk.Box()
            box.set_hexpand(True)
            box.set_vexpand(False)
            label = left_label(output['outputname'])
            switch = Gtk.Switch()
            switch.set_can_focus(False)
            switch.set_active(output['outputenabled'] == '1')
            switch.set_can_focus(False)
            name = output['outputname']
            id = output['outputid']
            box.pack_start(label, False, False, 10)
            box.pack_end(switch, False, False, 0)
            self._connect_switch(switch, id, name)

            if prev is None:
                self.add(box)
            else:
                self.attach_under(box, prev)
            prev = box
        self.show_all()


class SettingsMenu(Gtk.Popover):
    SIG_CONNECT_ATTEMPT = 'neonmeate-connect-attempt'
    SIG_MUSIC_DIR_UPDATED = 'neonmeate-musicdir-updated'
    SIG_UPDATE_REQUESTED = 'neonmeate-update-requested'
    SIG_OUTPUT_CHANGE = 'neonmeate-output-change'

    __gsignals__ = {
        SIG_CONNECT_ATTEMPT:
            (GObject.SignalFlags.RUN_FIRST, None, (str, int, bool,)),
        SIG_MUSIC_DIR_UPDATED: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        SIG_UPDATE_REQUESTED: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIG_OUTPUT_CHANGE: (GObject.SignalFlags.RUN_FIRST, None, (int, bool,))
    }

    def __init__(self, executor, configstate, connstatus, cfg):
        super(SettingsMenu, self).__init__()
        self._exec = executor
        self._cfg = cfg
        self._configstate = configstate
        self._connstatus = connstatus
        self._connstatus.connect('mpd_connected', self._on_mpd_connection)
        spacing = 16
        self.set_border_width(spacing)
        self._box = Gtk.VBox()
        self.add(self._box)

        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.LEFT)

        self._network_settings = NetworkSettings(configstate)
        self._library_settings = LibrarySettings(configstate, cfg)
        self._output_settings = OutputsSettings()

        notebook.append_page(self._network_settings, Gtk.Label('Network'))
        notebook.append_page(self._library_settings, Gtk.Label('Library'))
        notebook.append_page(self._output_settings, Gtk.Label('Outputs'))

        self._connect_label = Gtk.Label('Connect')
        self._connected_label = Gtk.Label('Connected')
        self._connect_switch = Gtk.ToggleButton()
        self._connect_switch.add(self._connect_label)
        self._connect_switch.connect(
            'notify::active',
            self._on_user_connect_change
        )

        self._connect_switch.set_property('margin_top', spacing)

        self._library_settings.connect(
            LibrarySettings.SIG_MUSIC_DIR_UPDATED,
            self._on_music_folder
        )

        self._library_settings.connect(
            LibrarySettings.SIG_CACHE_CLEARED,
            self._on_cache_clear
        )

        self._output_settings.connect(
            OutputsSettings.SIG_OUTPUT_CHANGE,
            self._on_outputs_change
        )

        self._box.add(notebook)
        self._box.add(self._connect_switch)
        self._box.show_all()

    def _on_cache_clear(self, widget):
        self._save()

    def on_outputs(self, outputs):
        self._output_settings.on_outputs(outputs)

    def _on_outputs_change(self, outputsmenu, id, enabled):
        self.emit(SettingsMenu.SIG_OUTPUT_CHANGE, id, enabled)

    def _on_mpd_connection(self, _, success):
        switch = self._connect_switch
        switch.set_active(success)
        label = self._connected_label if success else self._connect_label
        for c in switch.get_children():
            switch.remove(c)
        switch.add(label)
        switch.show_all()

    def _on_update_request(self, btn):
        self.emit(SettingsMenu.SIG_UPDATE_REQUESTED)

    def _on_save_settings(self, btn):
        self._save()

    def _save(self):
        self._cfg.save(main_config_file())

    def _on_music_folder(self, library_settings, chosen):
        self._save()
        self.emit(SettingsMenu.SIG_MUSIC_DIR_UPDATED, chosen)

    # This is called when the user toggles the connection
    # switch in the config panel. This will result in
    # _on_mpd_connection being called to update the label
    # text based on the current status.
    def _on_user_connect_change(self, switch, gparam):
        connected = switch.get_active()
        self._network_settings.on_user_connect_change(connected)
        host = self._network_settings.get_host_setting()
        port = self._network_settings.get_port_setting()
        self._configstate.set_host_and_port(host, port)
        self.emit('neonmeate-connect-attempt', host, port, connected)
