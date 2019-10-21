from gi.repository import Gtk, GObject


class ControlButton(Gtk.Button):
    def __init__(self, icon_name):
        super(ControlButton, self).__init__()
        self.icon_size = Gtk.IconSize.MENU
        self.icon = Gtk.Image.new_from_icon_name(icon_name, self.icon_size)
        self.add(self.icon)
        self.connect('clicked', self._on_clicked)
        self.click_handler = None

    def _on_clicked(self, widget):
        if self.click_handler:
            self.click_handler(widget)

    def set_click_handler(self, fn):
        self.click_handler = fn


class PlayPauseButton(ControlButton):
    def __init__(self):
        super(PlayPauseButton, self).__init__('media-playback-start')
        self.pause_icon = Gtk.Image.new_from_icon_name('media-playback-pause', self.icon_size)
        self.play_icon = self.icon
        self.connect('clicked', self.on_clicked)
        self.set_paused(False)
        self.paused = False

    def on_clicked(self, widget):
        self.set_paused(not self.paused)

    def set_paused(self, paused):
        child = self.get_child()
        if child == self.play_icon and paused:
            self._swap_icons()
        elif child == self.pause_icon and not paused:
            self._swap_icons()

    def _swap_icons(self):
        child = self.get_child()
        self.remove(child)
        new_icon = self.play_icon if child == self.pause_icon else self.pause_icon
        self.add(new_icon)
        self.get_child().show()
        self.paused = not self.paused


class ControlButtons(Gtk.ButtonBox):
    __gsignals__ = {
        'neonmeate_stop_playing': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_toggle_pause': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        super(ControlButtons, self).__init__(Gtk.Orientation.HORIZONTAL)
        self.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        self.play_pause_button = PlayPauseButton()
        self.stop_button = ControlButton('media-playback-stop')
        self.prev_song_button = ControlButton('media-skip-backward')
        self.next_song_button = ControlButton('media-skip-forward')

        self.stop_button.set_click_handler(self._on_stop_clicked)
        # self.play_button.set_click_handler(self._on_stop_clicked)

        for btn in [self.play_pause_button, self.stop_button, self.prev_song_button, self.next_song_button]:
            self.add(btn)

    def _on_playpause_clicked(self, btn):
        self.emit('neonmeate_toggle_pause')

    def _on_stop_clicked(self, btn):
        self.emit('neonmeate_stop_playing')
