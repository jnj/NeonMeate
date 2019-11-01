import gi

gi.require_version('GdkPixbuf', '2.0')

from gi.repository import GdkPixbuf, Gio, GLib, GObject


class ArtCache(GObject.GObject):
    def __init__(self):
        self._cache = {}

    def fetch(self, file_path, callback, user_data):
        if file_path in self._cache:
            callback(self._cache[file_path])
            return
        req = ArtRequest(file_path, callback)
        gio_file = Gio.File.new_for_path(file_path)
        gio_file.read_async(GLib.PRIORITY_DEFAULT, None, self._on_stream_ready, (req, user_data))

    def _on_stream_ready(self, src_object, result, user_data):
        try:
            stream = src_object.read_finish(result)
        except GLib.GError as e:
            print(e)
        else:
            GdkPixbuf.Pixbuf.new_from_stream_async(stream, None, self._on_pixbuf_ready, user_data)
        finally:
            pass

    def _on_pixbuf_ready(self, src_object, result, user_data):
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        req, other = user_data
        self._cache[req.file_path] = pixbuf
        req.on_completion(pixbuf)


class ArtRequest:
    def __init__(self, file_path, callback):
        self.file_path = file_path
        self.callback = callback

    def on_completion(self, art):
        self.callback(art)
