from gi.repository import Gtk, GObject

from ..util.config import main_config_file


class OutputsMenu(Gtk.VBox):
    SIG_OUTPUT_CHANGE = 'neonmeate-output-change'

    __gsignals__ = {
        SIG_OUTPUT_CHANGE: (GObject.SignalFlags.RUN_FIRST, None, (int, bool,))
    }

    def __init__(self):
        super(OutputsMenu, self).__init__()
        self._outputs = []
        self._update()

    def on_outputs(self, outputs):
        self._outputs.clear()
        self._outputs.extend(outputs)
        self._update()
        self.queue_draw()

    def _on_user_toggle(self, switch, gparam, name, id):
        enabled = switch.get_active()
        self.emit(OutputsMenu.SIG_OUTPUT_CHANGE, int(id), enabled)

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

        grid = Gtk.Grid()
        grid.set_property('margin', 10)
        grid.set_column_spacing(30)
        grid.set_row_spacing(10)
        self.add(grid)
        prev_label = None

        for output in self._outputs:
            grid_box = Gtk.Box()
            grid_box.set_hexpand(True)
            grid_box.set_vexpand(False)
            label = Gtk.Label(label=output['outputname'])
            label.set_xalign(0)
            label.set_justify(Gtk.Justification.LEFT)
            switch = Gtk.Switch()
            switch.set_can_focus(False)
            switch.set_active(output['outputenabled'] == '1')
            switch.set_can_focus(False)
            name = output['outputname']
            id = output['outputid']
            self._connect_switch(switch, id, name)

            grid_box.pack_start(label, False, False, 10)
            grid_box.pack_end(switch, False, False, 0)

            if prev_label is None:
                grid.add(grid_box)
            else:
                grid.attach_next_to(grid_box, prev_label,
                                    Gtk.PositionType.BOTTOM, 1, 1)

            prev_label = grid_box

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

        stack = Gtk.Stack()
        stack.set_hexpand(True)
        stack.set_vexpand(True)
        stack.set_property('margin-top', 20)
        spacing = 10

        self._menu_grid = Gtk.VBox()
        self.add(self._menu_grid)
        self.set_border_width(spacing)
        self._settings_grid = Gtk.Grid()
        self._settings_grid.set_column_spacing(spacing)
        self._settings_grid.set_row_spacing(spacing)
        self._settings_grid.set_property('margin', 10)

        host_label = Gtk.Label('Host')
        host_label.set_xalign(0)
        host_label.set_justify(Gtk.Justification.LEFT)
        self._settings_grid.add(host_label)
        host, port = self._configstate.get_host_and_port()
        self._host_entry = Gtk.Entry()
        self._host_entry.set_input_purpose(Gtk.InputPurpose.ALPHA)
        self._host_entry.set_text(host)
        self._settings_grid.add(self._host_entry)

        port_label = Gtk.Label('Port')
        port_label.set_xalign(0)
        port_label.set_justify(Gtk.Justification.LEFT)
        self._settings_grid.attach_next_to(port_label, host_label,
                                           Gtk.PositionType.BOTTOM, 1, 1)

        self._port_entry = Gtk.Entry()
        self._port_entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
        self._port_entry.set_text(str(port))
        self._settings_grid.attach_next_to(self._port_entry, port_label,
                                           Gtk.PositionType.RIGHT, 1, 1)

        music_dir_label = Gtk.Label('Music Folder')
        music_dir_label.set_xalign(0)
        music_dir_label.set_justify(Gtk.Justification.LEFT)
        music_dir_chooser = Gtk.FileChooserButton()
        music_dir_chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        music_dir_chooser.set_local_only(True)
        music_dir_chooser.set_current_folder(self._configstate.get_musicpath())
        music_dir_chooser.connect('file-set', self._on_music_folder)

        def __attach_below(to_attach, other_item):
            self._settings_grid.attach_next_to(
                to_attach, other_item,
                Gtk.PositionType.BOTTOM,
                1,
                1
            )

        __attach_below(music_dir_label, port_label)
        self._settings_grid.attach_next_to(music_dir_chooser, music_dir_label,
                                           Gtk.PositionType.RIGHT, 1, 1)

        albums_view_label = Gtk.Label('Artists')
        albums_view_label.set_xalign(0)
        albums_view_label.set_justify(Gtk.Justification.LEFT)
        __attach_below(albums_view_label, music_dir_label)
        self._include_comps = Gtk.ComboBoxText()
        self._include_comps.append('0', 'All')
        self._include_comps.append('1', 'Only album artists')
        include_comps = self._cfg.get_albums_include_comps()
        self._include_comps.set_active(0 if include_comps else 1)
        self._settings_grid.attach_next_to(self._include_comps,
                                           albums_view_label,
                                           Gtk.PositionType.RIGHT, 1, 1)
        self._include_comps.connect('changed', self._on_album_view_change)
        self._connect_label = Gtk.Label('Connect')
        self._connect_label.set_xalign(0)
        self._connect_label.set_justify(Gtk.Justification.LEFT)
        __attach_below(self._connect_label, albums_view_label)
        switch_box = Gtk.Box()
        self._connect_switch = Gtk.Switch()
        switch_box.pack_end(self._connect_switch, False, False, 0)
        self._settings_grid.attach_next_to(switch_box, self._connect_label,
                                           Gtk.PositionType.RIGHT, 1, 1)
        self._connect_switch.connect('notify::active',
                                     self._on_user_connect_change)

        self._update_btn = Gtk.Button(label='Update')
        self._update_btn.set_can_focus(False)
        self._update_btn.set_tooltip_text('Update the database')
        self._update_btn.connect('clicked', self._on_update_request)
        __attach_below(self._update_btn, switch_box)

        self._save_btn = Gtk.Button(label='Save')
        self._save_btn.set_can_focus(False)
        self._save_btn.connect('clicked', self._on_save_settings)
        __attach_below(self._save_btn, self._update_btn)

        self._clear_colors_btn = Gtk.Button(label='Clear Cache')
        self._clear_colors_btn.set_can_focus(False)
        self._clear_colors_btn.connect('clicked', self._on_clear_colors)
        __attach_below(self._clear_colors_btn, self._save_btn)
        self._settings_grid.show_all()
        self._outputs = OutputsMenu()
        self._outputs.connect(
            OutputsMenu.SIG_OUTPUT_CHANGE,
            self._on_outputs_change
        )

        stack.add_titled(self._settings_grid, 'settings', 'Settings')
        stack.add_titled(self._outputs, 'outputs', 'Outputs')
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)
        stack_switcher.set_can_focus(False)
        self._menu_grid.add(stack_switcher)
        self._menu_grid.add(stack)
        self._menu_grid.show_all()

    def on_outputs(self, outputs):
        self._outputs.on_outputs(outputs)

    def _on_outputs_change(self, outputsmenu, id, enabled):
        self.emit(SettingsMenu.SIG_OUTPUT_CHANGE, id, enabled)

    def _on_album_view_change(self, widget):
        active = self._include_comps.get_active()
        include_comps = active == 0
        self._cfg.set_albums_include_comps(include_comps)
        self._configstate.set_albums_include_comps(include_comps)

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

    # This is called when the user toggles the connection
    # switch in the config panel. This will result in
    # _on_mpd_connection being called to update the label
    # text based on the current status.
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
