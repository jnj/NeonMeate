import os

import gi

gi.require_version('GdkPixbuf', '2.0')

from gi.repository import GdkPixbuf, Gio, GLib, GObject


# noinspection PyUnresolvedReferences
class ArtCache(GObject.GObject):
    """
    Service for fetching album artwork. This assumes that the
    album artwork is located in <music_dir>/<artist>/<album>

    This does not use MPD's command for retrieving embedded
    album art; it assumes the music being played is located
    on the filesystem and it will read from there.
    """

    CoverNames = [f'{base}.{ext}'
                  for base in ['cover', 'front', 'folder', 'art']
                  for ext in ['jpg', 'png', 'gif']]

    def __init__(self, root_music_dir):
        self._cache = {}
        self._root_music_dir = root_music_dir
        self._pending_requests = {}
        self._cover_file_names = CoverNames

    def resolve_cover_file(self, dirpath):
        """
        Locates the cover artwork with the directory path given.
        Various artwork file name patterns will be tried.

        :param dirpath: directory relative to music dir
        :return: full path to the album art file,
        or None if it could not be found
        """
        for f in self._cover_file_names:
            fullpath = os.path.join(self._root_music_dir, dirpath, f)
            if os.path.exists(fullpath):
                return fullpath
        return None

    def fetch(self, file_path, callback, user_data):
        """
        Asynchronously loads the image at file_path
        and provides it to the callback as a GdkPixbuf
        instance.

        The caller can also supply arbitrary data for the
        user_data parameter and that will be given to the
        callback as well.
        """
        if file_path in self._cache:
            if callback is not None:
                callback(self._cache[file_path], user_data)
            return
        req = self._get_pending_or_create(file_path, callback, user_data)
        gio_file = Gio.File.new_for_path(file_path)
        gio_file.read_async(GLib.PRIORITY_DEFAULT, None, self._on_stream_ready, req)

    def _get_pending_or_create(self, file_path, callback, user_data):
        """
        Returns an ArtRequest for the path. If there is already
        one pending, then it will be returned. Otherwise, creates
        a new one.
        """
        if file_path in self._pending_requests:
            r = self._pending_requests[file_path]
            r.add_callback(callback, user_data)
        else:
            r = ArtRequest(file_path, callback, user_data)
            self._pending_requests[file_path] = r
        return r

    def _on_stream_ready(self, src_object, result, art_request):
        try:
            stream = src_object.read_finish(result)
        except GLib.GError as e:
            # todo handle better
            print(e)
        else:
            GdkPixbuf.Pixbuf.new_from_stream_async(stream, None, self._on_pixbuf_ready, art_request)
        finally:
            pass

    def _on_pixbuf_ready(self, src_object, result, art_request):
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        self._cache[art_request.file_path] = pixbuf
        art_request.on_completion(pixbuf)
        if art_request.file_path in self._pending_requests:
            del self._pending_requests[art_request.file_path]


class ArtRequest:
    """
    A request to fetch an image file. Once the file has
    been loaded, the associated callbacks will be called
    on the GTK main thread.
    """
    def __init__(self, file_path, callback, user_data):
        self.file_path = file_path
        self._callbacks = []
        self.add_callback(callback, user_data)

    def add_callback(self, callback, user_data):
        if callback is not None:
            self._callbacks.append((callback, user_data))

    def on_completion(self, art):
        for callback, user_data in self._callbacks:
            callback(art, user_data)
