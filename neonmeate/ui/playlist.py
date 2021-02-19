import neonmeate.ui.toolkit as tk

from gi.repository import Gdk, GObject, Gtk
from neonmeate.ui.controls import NeonMeateButtonBox, ControlButton


# noinspection PyUnresolvedReferences
class PlayListControls(NeonMeateButtonBox):
    __gsignals__ = {
        'neonmeate_clear_playlist': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        super(PlayListControls, self).__init__()
        clear_btn = self._add_button(
            ControlButton('edit-clear'),
            'clear',
            'neonmeate_clear_playlist'
        )
        clear_btn.set_label("Clear")
        clear_btn.set_always_show_image(True)
        clear_btn.set_tooltip_text('Clear the play queue')


# noinspection PyUnresolvedReferences
class PlaylistContainer(Gtk.Frame):
    def __init__(self, mpdclient):
        super(PlaylistContainer, self).__init__()
        self._mpdclient = mpdclient
        self._box = Gtk.VBox()
        self._playlist_controls = Gtk.ActionBar()
        self._controls = PlayListControls()
        self._playlist_controls.pack_start(self._controls)
        self._playlist = Playlist()
        self._playlist.connect('neonmeate-delitem-playlist', self._on_del_item)
        self.add(self._box)
        self._box.pack_start(self._playlist, True, True, 0)
        self._box.pack_end(self._playlist_controls, False, False, 0)
        self._playlist.show()
        self._playlist_controls.show()
        self._box.show_all()
        self._box.show()
        self._controls.connect('neonmeate_clear_playlist', self._on_clear)

    def _on_del_item(self, pl, idx):
        self._mpdclient.delete_playlist_item(idx)

    def _on_clear(self, _):
        self._mpdclient.clear_playlist()

    def clear(self):
        self._playlist.clear()

    def add_playlist_item(self, item):
        self._playlist.add_playlist_item(item)


# noinspection PyUnresolvedReferences
class Playlist(tk.Scrollable):
    __gsignals__ = {
        'neonmeate_clear_playlist': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_delitem_playlist':
            (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    def __init__(self):
        super(Playlist, self).__init__()
        self._playlist_table = tk.Table(
            ['Track', 'Artist', 'Album', 'Title', 'Time', 'Index'],
            [int, str, str, str, str, int],
            ['Track', 'Artist', 'Album', 'Title', 'Time']
        )
        self._selected_row = None
        self._widget = self._playlist_table.as_widget()
        self.add_content(self._widget)
        self._playlist_table.set_selection_handler(self._on_selection)
        self._widget.connect('key-press-event', self._on_keypress)

    def _on_keypress(self, treeview, eventkey):
        if eventkey.keyval == Gdk.KEY_Down or \
                eventkey.keyval == Gdk.KEY_Up or \
                eventkey.keyval == Gdk.KEY_Left or \
                eventkey.keyval == Gdk.KEY_Right:
            return False
        if eventkey.keyval == Gdk.KEY_Delete:
            if self._selected_row:
                index = self._selected_row[5]
                self.emit('neonmeate_delitem_playlist', index)
        return True

    def _on_selection(self, row):
        self._selected_row = row

    def clear(self):
        self._playlist_table.clear()

    def add_playlist_item(self, item):
        l = [
            item['track'],
            item['artist'],
            item['album'],
            item['title'],
            (Playlist.format_time(item['seconds'])),
            item['position']
        ]
        self._playlist_table.add(l)

    @staticmethod
    def format_time(seconds):
        m, s = divmod(seconds, 60)

        if m > 60:
            h, m = divmod(m, 60)
            return f'{h:02}:{m:02}:{s:02}'

        return f'{m:02}:{s:02}'
