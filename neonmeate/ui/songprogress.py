from gi.repository import Gtk


# noinspection PyUnresolvedReferences
class SongProgress(Gtk.ProgressBar):

    @staticmethod
    def _to_int(value):
        return int(round(value, 0))

    def __init__(self):
        super(SongProgress, self).__init__()
        self.set_valign(Gtk.Align.CENTER)
        self.set_hexpand(True)
        self.set_fraction(0)
        self._total_seconds = 0.1
        self._elapsed_seconds = 0.0

    def set_elapsed(self, elapsed, total):
        elapsed_secs = SongProgress._to_int(elapsed)
        total_secs = SongProgress._to_int(total)

        if (elapsed_secs != self._elapsed_seconds) or \
                (total_secs != self._total_seconds):
            self._on_change(elapsed_secs, total_secs)

    def _on_change(self, elapsed_seconds, total_seconds):
        self._elapsed_seconds = elapsed_seconds
        self._total_seconds = total_seconds
        self.set_fraction(round(elapsed_seconds / total_seconds, 2))
        elapsed_min, elapsed_sec = divmod(elapsed_seconds, 60)
        total_min, total_sec = divmod(total_seconds, 60)
        mmss = f'{elapsed_min}:{elapsed_sec:02} / {total_min}:{total_sec:02}'
        self.set_tooltip_text(mmss)
        self.queue_draw()

    def set_fraction(self, frac):
        super(SongProgress, self).set_fraction(frac)
