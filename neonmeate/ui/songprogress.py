from gi.repository import Gtk


class SongProgress(Gtk.LevelBar):
    def __init__(self):
        super(SongProgress, self).__init__()
        self.set_min_value(0)
        self.set_max_value(100)
        self.set_valign(Gtk.Align.CENTER)
        self.set_hexpand(True)
        self.set_value(0)
        self.set_mode(Gtk.LevelBarMode.CONTINUOUS)
