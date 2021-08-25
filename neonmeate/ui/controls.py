from gi.repository import Gtk, GObject


# noinspection PyUnresolvedReferences
class ControlButton(Gtk.Button):
    def __init__(self, icon_name):
        super(ControlButton, self).__init__()
        self.icon_size = Gtk.IconSize.MENU
        self.icon = Gtk.Image.new_from_icon_name(icon_name, self.icon_size)
        self.add(self.icon)


# noinspection PyUnresolvedReferences
class PlayModeButton(Gtk.ToggleButton):
    def __init__(self, icon_name, label=None):
        super(PlayModeButton, self).__init__()
        if icon_name is not None:
            self._icon_size = Gtk.IconSize.MENU
            self._icon = Gtk.Image.new_from_icon_name(
                icon_name,
                self._icon_size
            )
            self.add(self._icon)
        else:
            lbl = Gtk.Label()
            lbl.set_label(label)
            self.add()


# noinspection PyUnresolvedReferences
class VolumeControl(Gtk.VolumeButton):
    def __init__(self):
        super(VolumeControl, self).__init__()
        self.set_property('use-symbolic', True)


# noinspection PyUnresolvedReferences
class PlayPauseButton(ControlButton):
    __gsignals__ = {
        'neonmeate_playpause_toggled':
            (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self):
        super(PlayPauseButton, self).__init__('media-playback-start')
        self.pause_icon = Gtk.Image.new_from_icon_name(
            'media-playback-pause',
            self.icon_size
        )
        self.play_icon = self.icon
        self.paused = False
        self.set_paused(False)
        self.connect('clicked', self._toggle_pause_state)

    def set_play_icon(self):
        child = self.get_child()
        if not child == self.play_icon:
            self._swap_icons()

    def set_paused(self, paused):
        child = self.get_child()
        if child == self.play_icon and not paused:
            self._swap_icons()
        elif child == self.pause_icon and paused:
            self._swap_icons()

    def _toggle_pause_state(self, button):
        self.set_paused(not self.paused)
        self.emit('neonmeate_playpause_toggled', self.paused)

    def _swap_icons(self):
        child = self.get_child()
        self.remove(child)
        new_icon = self._switch_icon(child)
        self.add(new_icon)
        self.get_child().show()
        self.paused = not self.paused

    def _switch_icon(self, child):
        if child == self.pause_icon:
            return self.play_icon
        return self.pause_icon


# noinspection PyUnresolvedReferences
class NeonMeateButtonBox(Gtk.ButtonBox):
    def __init__(self):
        super(NeonMeateButtonBox, self).__init__(Gtk.Orientation.HORIZONTAL)
        self.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        self._buttons = []
        self._byname = {}

    def _add_button(self, button, name, click_signal_name):
        self._buttons.append(button)
        self._byname[name] = button
        self.add(button)
        if click_signal_name is not None:
            self._emit_on_click(button, click_signal_name)
        return button

    def _emit_on_click(self, button, signal_name):
        def click_handler(_):
            self.emit(signal_name)

        button.connect('clicked', click_handler)


# noinspection PyUnresolvedReferences
class ControlButtons(NeonMeateButtonBox):
    __gsignals__ = {
        'neonmeate_stop_playing': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_start_playing': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_toggle_pause': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_prev_song': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_next_song': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        super(ControlButtons, self).__init__()

        self._prev = self._add_button(
            ControlButton('media-skip-backward'),
            'prev',
            'neonmeate_prev_song'
        )
        self._stop = self._add_button(
            ControlButton('media-playback-stop'),
            'stop',
            'neonmeate_stop_playing'
        )
        self._play_pause_button = self._add_button(
            PlayPauseButton(),
            'play_pause',
            None
        )
        self._next = self._add_button(
            ControlButton('media-skip-forward'),
            'next',
            'neonmeate-next-song'
        )
        self._play_pause_button.connect(
            'neonmeate_playpause_toggled',
            self._on_playpause
        )

    def set_paused(self, paused, stopped):
        if stopped:
            self._play_pause_button.set_play_icon()
        else:
            self._play_pause_button.set_paused(paused)

    def _on_playpause(self, btn, is_paused):
        if is_paused:
            self.emit('neonmeate_toggle_pause')
        else:
            self.emit('neonmeate_start_playing')
        return True


# noinspection PyUnresolvedReferences
class PlayModeButtons(NeonMeateButtonBox):
    __gsignals__ = {
        'neonmeate_playmode_toggle': (
            GObject.SignalFlags.RUN_FIRST, None, (str, bool))
    }

    def __init__(self):
        super(PlayModeButtons, self).__init__()
        self._consume = self._add_button(
            PlayModeButton('view-refresh'),
            'consume',
            None
        )
        self._single = self._add_button(
            PlayModeButton('zoom-original', '1'),
            'single',
            None
        )
        self._random = self._add_button(
            PlayModeButton('media-playlist-shuffle'),
            'random',
            None
        )
        self._repeat = self._add_button(
            PlayModeButton('media-playlist-repeat'),
            'repeat',
            None
        )
        # self._vol_control = self._add_button(
        #     VolumeControl(),
        #     'volume',
        #     None
        # )
        self._consume.set_tooltip_text('Consume mode')
        self._single.set_tooltip_text('Single mode')
        self._random.set_tooltip_text('Random mode')
        self._repeat.set_tooltip_text('Repeat mode')
        self._subscribers_by_signal = {}
        for name, btn in self._byname.items():
            btn.connect('clicked', self._on_click(name, btn))

    def subscribe_to_signal(self, signal, handler):
        handler_id = self.connect(signal, handler)
        handlers = self._subscribers_by_signal.get(signal, [])
        handlers.append(handler_id)
        self._subscribers_by_signal[signal] = handlers

    def _on_click(self, name, btn):
        def handler(_):
            self.emit('neonmeate_playmode_toggle', name, btn.get_active())

        return handler

    def _disable_emission(self, signal_name):
        for handler_id in self._subscribers_by_signal.get(signal_name, []):
            self.handler_block(handler_id)

    def _enable_emission(self, signal_name):
        for handler_id in self._subscribers_by_signal.get(signal_name, []):
            self.handler_unblock(handler_id)

    def on_mode_change(self, name, active):
        btn = self._byname.get(name, None)
        if btn and btn.get_active() != active:
            signal_name = 'neonmeate_playmode_toggle'
            try:
                self._disable_emission(signal_name)
                btn.set_active(active)
            finally:
                self._enable_emission(signal_name)
