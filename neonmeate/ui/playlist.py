import neonmeate.ui.toolkit as tk

from gi.repository import Gdk


class Playlist(tk.Scrollable):
    def __init__(self):
        super(Playlist, self).__init__()
        self._playlist_table = tk.Table(['Artist', 'Album', 'Track', 'Title'], [str, str, int, str])
        self._widget = self._playlist_table.as_widget()
        self.add_content(self._widget)
        self._playlist_table.set_selection_handler(self._on_selection)
        self._widget.connect('key-press-event', self._on_keypress)

    def _on_keypress(self, treeview, eventkey):
        if eventkey.keyval == Gdk.KEY_c:
            print("User pressed 'c'")
        elif eventkey.keyval == Gdk.KEY_Down or \
             eventkey.keyval == Gdk.KEY_Up or \
             eventkey.keyval == Gdk.KEY_Left or \
             eventkey.keyval == Gdk.KEY_Right:
            return False
        return True

    def _on_selection(self, treeiter):
        print(f"selected {treeiter}")

    def clear(self):
        self._playlist_table.clear()

    def add_playlist_item(self, item):
        self._playlist_table.add(item)
