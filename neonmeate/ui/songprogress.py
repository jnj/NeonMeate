from gi.repository import Gtk


# noinspection PyUnresolvedReferences
class SongProgress(Gtk.ProgressBar):
    def __init__(self):
        super(SongProgress, self).__init__()
        self.set_valign(Gtk.Align.CENTER)
        self.set_hexpand(True)
        self.set_fraction(0)
        self._total_seconds = 1.0
        self._elapsed_seonds = 0.0

    def set_elapsed(self, elapsed, total):
        elapsed_seconds = int(round(elapsed, 0))
        total_seconds = int(round(total, 0))

        if elapsed_seconds != self._elapsed_seonds or total_seconds != self._total_seconds:
            self._on_change(elapsed_seconds, total_seconds)

    def _on_change(self, elapsed_seconds, total_seconds):
        self._elapsed_seconds = elapsed_seconds
        self._total_seconds = total_seconds
        fraction = round(elapsed_seconds / total_seconds, 2)
        self.set_fraction(fraction)
        elapsed_min, elapsed_sec = divmod(elapsed_seconds, 60)
        total_min, total_sec = divmod(total_seconds, 60)
        self.set_tooltip_text(f'{elapsed_min}:{elapsed_sec:02} / {total_min}:{total_sec:02}')
        self.queue_draw()

    def set_fraction(self, frac):
        super(SongProgress, self).set_fraction(frac)



