import concurrent.futures as fut
import queue
import sched
import threading
import time

from gi.repository import GLib


def signal_subcribe_on_main(connect_fn, signal_name, callback, *args):
    """Connects a signal handler so that it will be run on the main GTK thread"""

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
            action()

    def stop(self):
        self._running.set(False)

    def _is_running(self):
        return self._running.get()


class ScheduledExecutor:
    def __init__(self):
        self._thread = EventLoopThread()
        self._scheduler = sched.scheduler(timefunc=time.monotonic)

    def start(self):
        self._thread.start()

    def stop(self):
        self._thread.stop()

    def execute(self, action):
        self._thread.add(action)

    def schedule(self, delay, action):
        def run_on_event_thread():
            self.execute(action)

        self._scheduler.enter(delay, 1, run_on_event_thread)
        t = threading.Thread(target=self._scheduler.run)
        t.start()

    def schedule_periodic(self, delay, action):
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
