from gi.repository import Gtk, Gdk, GObject, Gio


class PlayPauseButton(Gtk.Button):
    def __init__(self):
        super(PlayPauseButton, self).__init__()
        icon_size = Gtk.IconSize.MENU
        self.pause_icon = Gtk.Image.new_from_icon_name('media-playback-pause', icon_size)
        self.play_icon = Gtk.Image.new_from_icon_name('media-playback-start', icon_size)
        self.add(self.play_icon)
        self.paused = False
        self.connect('clicked', self.on_clicked)
        self.set_paused(False)

    def on_clicked(self, widget):
        print("play/pause clicked!")
        self.set_paused(not self.paused)

    def set_paused(self, paused):
        if self.paused == paused:
            return
        if self.get_child():
            self.remove(self.get_child())
        if paused:
            self.add(self.pause_icon)
        else:
            self.add(self.play_icon)
        self.paused = paused
        self.get_child().show()


class ControlButton(Gtk.Button):
    def __init__(self, icon_name):
        super(ControlButton, self).__init__()
        self.icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
        self.add(self.icon)
        self.connect('clicked', self.on_clicked)
        self.click_handler = None

    def on_clicked(self, widget):
        if self.click_handler:
            self.click_handler(widget)

    def set_click_handler(self, fn):
        self.click_handler = fn


class ControlButtons(Gtk.ButtonBox):
    __gsignals__ = {
        'neonmeate_stop_playing': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        super(ControlButtons, self).__init__(Gtk.Orientation.HORIZONTAL)
        self.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        self.play_pause_button = PlayPauseButton()
        self.stop_button = ControlButton('media-playback-stop')
        self.prev_song_button = ControlButton('media-skip-backward')
        self.next_song_button = ControlButton('media-skip-forward')

        self.stop_button.set_click_handler(self._on_stop_clicked)

        for btn in [self.play_pause_button, self.stop_button, self.prev_song_button, self.next_song_button]:
            self.add(btn)

    def _on_stop_clicked(self, btn):
        self.emit('neonmeate_stop_playing')
        print('stop clicked')
