import queue
import sched
import threading
import time
import _thread
from concurrent.futures import ThreadPoolExecutor
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
        self._thread = EventLoopThread()
        self._scheduler = sched.scheduler(timefunc=time.monotonic)
        self._executor = ThreadPoolExecutor()
        self._stopped = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        self._thread.start()

    def stop(self):
        self._stopped = True
        self._thread.stop()
        self._executor.shutdown(wait=True)

    def submit(self, task, *args, **kwargs):
        return self._executor.submit(task, *args, **kwargs)

    def execute(self, action):
        self._thread.add(action)

    def schedule(self, delay, action):
        if self._stopped:
            return

        return ScheduledTask(delay, action, self._scheduler, self._executor,
                             self._thread, False)

    def schedule_periodic(self, delay, action):
        if self._stopped:
            return
        return ScheduledTask(delay, action, self._scheduler, self._executor,
                             self._thread, True)


class ScheduledTask:
    def __init__(self, delay, action, scheduler, executor, eventloop, repeat):
        self._delay = delay
        self._sched = scheduler
        self._exec = executor
        self._eventloop = eventloop
        self._action = action

        def run():
            self._eventloop.add(action)

        if repeat:
            self._schedule_periodic(run)
        else:
            self._schedule(run)

    def _schedule_periodic(self, to_run):
        def run():
            to_run()
            self._schedule_periodic(to_run)

        self._schedule(run)

    def _schedule(self, to_run):
        self._event = self._sched.enter(self._delay, -1, to_run)
        _thread.start_new_thread(self._sched.run, ())

    def cancel(self):
        try:
            self._sched.cancel(self._event)
        except ValueError:
            pass


if __name__ == '__main__':
    def sayhi():
        print("hi!")


    executor = ScheduledExecutor()
    executor.start()
    e = executor.schedule_periodic(0.5, sayhi)
    print('sleeping...')
    time.sleep(3)
    e.cancel()
    executor.stop()
    time.sleep(3)
    print("done")
