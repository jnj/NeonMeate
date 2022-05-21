import neonmeate.ui.toolkit as tk

from gi.repository import Gdk, GObject, Gtk
from neonmeate.ui.controls import NeonMeateButtonBox, ControlButton
from neonmeate.ui.random_widget import RandomWidget
from .times import format_seconds


class PlayListControls(NeonMeateButtonBox):
    SIG_CLEAR_PLAYLIST = 'neonmeate_clear_playlist'
    SIG_CROP_PLAYLIST = 'neonmeate_crop_playlist'
    SIG_SHUFFLE_PLAYLIST = 'neonmeate_shuffle_playlist'

    __gsignals__ = {
        SIG_CLEAR_PLAYLIST : (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIG_CROP_PLAYLIST : (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIG_SHUFFLE_PLAYLIST: (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        super(PlayListControls, self).__init__()
        crop_btn = self.add_button(
            ControlButton('crop'),
            'crop',
            PlayListControls.SIG_CROP_PLAYLIST
        )
        crop_btn.set_label('Crop')
        # crop_btn.set_always_show_image(True)
        crop_btn.set_tooltip_text('Remove all except first song')
        clear_btn = self.add_button(
            ControlButton('edit-clear'),
            'clear',
            PlayListControls.SIG_CLEAR_PLAYLIST
        )
        clear_btn.set_label('Clear')
        # clear_btn.set_always_show_image(True)
        clear_btn.set_tooltip_text('Clear the play queue')
        shufl_btn = self.add_button(
            ControlButton('shuffle'),
            'shuffle',
            PlayListControls.SIG_SHUFFLE_PLAYLIST
        )
        shufl_btn.set_label('Shuffle')
        # shufl_btn.set_always_show_image(True)
        shufl_btn.set_tooltip_text('Shuffle the play queue')


class PlaylistContainer(Gtk.Frame):
    SIG_PENDING_PLAYLIST_CHG = 'neonmeate_playlist_change'
    SIG_RANDOM_FILL = 'neonmeate_random_fill'

    __gsignals__ = {
        SIG_RANDOM_FILL: (GObject.SignalFlags.RUN_FIRST, None, (str, int)),
        SIG_PENDING_PLAYLIST_CHG: (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, mpdclient):
        super(PlaylistContainer, self).__init__()
        self._mpdclient = mpdclient
        self._box = Gtk.Box()
        self._box.set_orientation(Gtk.Orientation.VERTICAL)
        self._playlist_controls_bar = Gtk.ActionBar()
        self._controls = PlayListControls()
        self._playlist_controls_bar.pack_start(self._controls)
        self._rand = RandomWidget()
        self._playlist_controls_bar.pack_end(self._rand)
        self._playlist = Playlist()
        self._playlist.connect(
            Playlist.SIG_DEL_PLAYLIST_ITEM,
            self._on_del_item
        )
        self.add(self._box)
        self._box.pack_start(self._playlist, True, True, 0)
        self._box.pack_end(self._playlist_controls_bar, False, False, 0)
        self._controls.connect(
            PlayListControls.SIG_CROP_PLAYLIST,
            self._on_crop
        )
        self._controls.connect(
            PlayListControls.SIG_CLEAR_PLAYLIST,
            self._on_clear
        )
        self._controls.connect(
            PlayListControls.SIG_SHUFFLE_PLAYLIST,
            self._on_shuffle
        )
        self._rand.connect(RandomWidget.SIG_RANDOM_ADDED, self._on_add_random)
        self._box.show_all()

    def _on_add_random(self, widget, item_type, n):
        self.emit(PlaylistContainer.SIG_PENDING_PLAYLIST_CHG)
        self.emit(PlaylistContainer.SIG_RANDOM_FILL, item_type, n)

    def _on_del_item(self, pl):
        for i in pl.get_selected_indices():
            self._mpdclient.delete_playlist_item(i)

    def _on_shuffle(self, _):
        self.emit(PlaylistContainer.SIG_PENDING_PLAYLIST_CHG)
        self._mpdclient.shuffle_playlist()

    def _on_clear(self, _):
        self.emit(PlaylistContainer.SIG_PENDING_PLAYLIST_CHG)
        self._mpdclient.clear_playlist()

    def _on_crop(self, _):
        self.emit(PlaylistContainer.SIG_PENDING_PLAYLIST_CHG)
        self._mpdclient.crop_playlist()

    def clear(self):
        self._playlist.clear()

    def add_playlist_item(self, item):
        self._playlist.add_playlist_item(item)


class Playlist(Gtk.ScrolledWindow):
    SIG_DEL_PLAYLIST_ITEM = 'neonmeate_delitem_playlist'

    __gsignals__ = {
        SIG_DEL_PLAYLIST_ITEM: (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    @staticmethod
    def format_track_no(track_no):
        return f'{int(track_no):02}'

    def __init__(self):
        super(Playlist, self).__init__()
        self._playlist_table = tk.Table(
            ['Track', 'Artist', 'Album', 'Title', 'Time', 'Index'],
            [str, str, str, str, str, int],
            ['Track', 'Artist', 'Album', 'Title', 'Time'],
            [False, True, True, True, True, True]
        )
        self._selected_indices = []
        self._treeview = self._playlist_table.as_widget()
        self.append(self._treeview)
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
                self.emit(Playlist.SIG_DEL_PLAYLIST_ITEM)
        return True

    def _on_selection(self, row):
        self._selected_row = row

    def clear(self):
        self._playlist_table.clear()

    def add_playlist_item(self, item):
        row = [
            Playlist.format_track_no(item['track']),
            item['artist'],
            item['album'],
            item['title'],
            format_seconds(item['seconds']),
            item['position']
        ]
        self._playlist_table.add(row)
