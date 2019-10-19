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


class ControlButtons(Gtk.ButtonBox):
    def __init__(self):
        super(ControlButtons, self).__init__()


