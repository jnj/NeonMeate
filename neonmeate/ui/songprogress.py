from gi.repository import Gtk


# noinspection PyUnresolvedReferences
class SongProgress(Gtk.ProgressBar):
    def __init__(self):
        super(SongProgress, self).__init__()
        self.set_valign(Gtk.Align.CENTER)
        self.set_hexpand(True)
        self.set_fraction(0)

    def set_fraction(self, frac):
        super(SongProgress, self).set_fraction(frac)
        self.set_tooltip_text(f'{frac}')

