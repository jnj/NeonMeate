import neonmeate.ui.toolkit as tk


class Playlist(tk.Scrollable):
    def __init__(self):
        super(Playlist, self).__init__()
        self._playlist_table = tk.Table(['Artist', 'Album', 'Track', 'Title'], [str, str, int, str])
        self.add_content(self._playlist_table.as_widget())

    def clear(self):
        self._playlist_table.clear()

    def add_playlist_item(self, item):
        self._playlist_table.add(item)

