import neonmeate.ui.toolkit as tk

from gi.repository import Gdk, GObject, Gtk
from neonmeate.ui.controls import NeonMeateButtonBox, ControlButton
from .times import format_seconds

# noinspection PyUnresolvedReferences
class PlayListControls(NeonMeateButtonBox):
    __gsignals__ = {
        'neonmeate_clear_playlist': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_shuffle_playlist': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_random_fill': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        super(PlayListControls, self).__init__()
        clear_btn = self.add_button(
            ControlButton('edit-clear'),
            'clear',
            'neonmeate_clear_playlist'
        )
        clear_btn.set_label("Clear")
        clear_btn.set_always_show_image(True)
        clear_btn.set_tooltip_text('Clear the play queue')
        shufl_btn = self.add_button(
            ControlButton('shuffle'),
            'shuffle',
            'neonmeate_shuffle_playlist'
        )
        shufl_btn.set_label('Shuffle')
        shufl_btn.set_always_show_image(True)
        shufl_btn.set_tooltip_text('Shuffle the play queue')
        randm_btn = self.add_button(
            ControlButton('random'),
            'random',
            'neonmeate_random_fill'
        )
        randm_btn.set_always_show_image(True)
        randm_btn.set_tooltip_text("Add random songs to the play queue")
        randm_btn.set_label('Random')


# noinspection PyUnresolvedReferences
class PlaylistContainer(Gtk.Frame):
    __gsignals__ = {
        'neonmeate_random_fill': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, mpdclient):
        super(PlaylistContainer, self).__init__()
        self._mpdclient = mpdclient
        self._box = Gtk.VBox()
        self._playlist_controls_bar = Gtk.ActionBar()
        self._controls = PlayListControls()
        self._playlist_controls_bar.pack_start(self._controls)
        self._playlist = Playlist()
        self._playlist.connect('neonmeate-delitem-playlist', self._on_del_item)
        self.add(self._box)
        self._box.pack_start(self._playlist, True, True, 0)
        self._box.pack_end(self._playlist_controls_bar, False, False, 0)
        self._box.show_all()
        self._controls.connect('neonmeate_clear_playlist', self._on_clear)
        self._controls.connect('neonmeate_shuffle_playlist', self._on_shuffle)
        self._controls.connect('neonmeate_random_fill', self._rand_fill)

    def _on_del_item(self, pl):
        indices = pl.get_selected_indices()
        for i in indices:
            self._mpdclient.delete_playlist_item(i)

    def _on_shuffle(self, _):
        self._mpdclient.shuffle_playlist()

    def _rand_fill(self, _):
        self.emit('neonmeate_random_fill')

    def _on_clear(self, _):
        self._mpdclient.clear_playlist()

    def clear(self):
        self._playlist.clear()

    def add_playlist_item(self, item):
        self._playlist.add_playlist_item(item)


# noinspection PyUnresolvedReferences
class Playlist(Gtk.ScrolledWindow):
    __gsignals__ = {
        'neonmeate_clear_playlist': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_delitem_playlist': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    @staticmethod
    def format_track_no(track_no):
        return f'{int(track_no):02}'

    def __init__(self):
        super(Playlist, self).__init__()
        self._playlist_table = tk.Table(
            ['Track', 'Artist', 'Album', 'Title', 'Time', 'Index'],
            [str, str, str, str, str, int],
            ['Track', 'Artist', 'Album', 'Title', 'Time']
        )
        self._selected_indices = []
        self._treeview = self._playlist_table.as_widget()
        self.add(self._treeview)
        self._playlist_table.set_selection_handler(self._on_selection)
        self._treeview.connect('key-press-event', self._on_keypress)
        self._nav_keys = {
            Gdk.KEY_Down,
            Gdk.KEY_Up,
            Gdk.KEY_Left,
            Gdk.KEY_Right
        }

    def get_selected_indices(self):
        return sorted(self._selected_indices, reverse=True)

    def _on_keypress(self, treeview, eventkey):
        if eventkey.keyval in self._nav_keys:
            return False
        if eventkey.keyval == Gdk.KEY_Delete:
            selection = treeview.get_selection()
            self._selected_indices.clear()

            def on_selected_row(treemodel, _, model_iter):
                row = treemodel[model_iter]
                self._selected_indices.append(row[5])

            selection.selected_foreach(on_selected_row)

            if self._selected_indices:
                self.emit('neonmeate_delitem_playlist')
        return True

    def _on_selection(self, row):
        self._selected_row = row

    def clear(self):
        self._playlist_table.clear()

    def add_playlist_item(self, item):
        l = [
            Playlist.format_track_no(item['track']),
            item['artist'],
            item['album'],
            item['title'],
            format_seconds(item['seconds']),
            item['position']
        ]
        self._playlist_table.add(l)
