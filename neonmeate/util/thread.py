import queue
import sched
import threading
import time
from  concurrent.futures import ThreadPoolExecutor
from gi.repository import GLib


def signal_subcribe_on_main(connect_fn, signal_name, callback, *args):
    """Subscribes to a signal on the GTK thread."""

    def run_on_main_thread(obj, *a):
        GLib.idle_add(callback, obj, *a)

    connect_fn(signal_name, run_on_main_thread, *args)


class AtomicBoolean:
    def __init__(self, initial=False):
        self._boolean = initial
        self._lock = threading.RLock()
        self.set(initial)

    def set(self, b):
        with self._lock:
            self._boolean = b

    def get(self):
        with self._lock:
            return self._boolean


class EventLoopThread(threading.Thread):
    def __init__(self):
        super(EventLoopThread, self).__init__(daemon=True)
        self._queue = queue.SimpleQueue()
        self._running = AtomicBoolean(False)

    def add(self, action):
        self._queue.put(action)

    def run(self):
        self._running.set(True)
        while self._is_running():
            action = self._queue.get()
            if action:
                action()

    def stop(self):
        self._running.set(False)

    def _is_running(self):
        return self._running.get()


class ScheduledExecutor:
    def __init__(self):
        self._thread = None
        self._scheduler = sched.scheduler(timefunc=time.monotonic)
        self._executor = ThreadPoolExecutor()
        self._stopped = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        if self._thread is None:
            self._thread = EventLoopThread()
        self._thread.start()

    def stop(self):
        self._stopped = True
        if self._thread is not None:
            self._thread.stop()
            self._thread = None
        self._executor.shutdown(wait=True)

    def execute(self, action):
        self._thread.add(action)

    def schedule(self, delay, action):
        if self._stopped:
            return

        def run_on_event_thread():
            self.execute(action)

        self._scheduler.enter(delay, 1, run_on_event_thread)
        self._executor.submit(self._scheduler.run)

    def schedule_periodic(self, delay, action):
        if self._stopped:
            return

        def run_and_requeue():
            action()
            self.schedule_periodic(delay, action)

        self.schedule(delay, run_and_requeue)


if __name__ == '__main__':
    def sayhi():
        print("hi!")

    executor = ScheduledExecutor()
    executor.start()
    executor.schedule_periodic(1.0, sayhi)
    print('sleeping...')
    time.sleep(4)
    executor.stop()
    time.sleep(3)
    print("done")
