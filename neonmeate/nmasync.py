import sched
import threading
import time

from gi.repository import GLib


def signal_subcribe_on_main(connect_fn, signal_name, callback, *args):
    """Connects a signal handler so that it will be run on the main GTK thread"""

    def run_on_main_thread(obj, *a):
        GLib.idle_add(callback, obj, *a)

    connect_fn(signal_name, run_on_main_thread, *args)


class RunAsync(threading.Thread):
    """
    A one-shot asynchronous operation. Runs the runnable on a
    new thread.
    """

    def __init__(self, runnable):
        super(RunAsync, self).__init__(group=None, target=self._exec_runnable, daemon=True)
        self._runnable = runnable
        self.start()

    def _exec_runnable(self):
        self._runnable()


class PeriodicTask(threading.Thread):
    """
    Thread that will execute its action repeatedly on a fixed interval.
    """

    def __init__(self, delay_millis, target):
        super(PeriodicTask, self).__init__(group=None, target=self._repeat, daemon=True)
        self._scheduler = sched.scheduler(timefunc=time.monotonic)
        self._delay = delay_millis / 1000.0
        self._runnable = target
        self._running = True

    def stop(self):
        self._running = False

    def _schedule_next(self):
        self._scheduler.enter(self._delay, 1, self._runnable)

    def _repeat(self):
        while self._running:
            self._schedule_next()
            self._scheduler.run()


if __name__ == '__main__':
    def sayhi():
        print("hi!")


    t = PeriodicTask(200, sayhi)
    t.start()
    t.join(timeout=10.0)

    t.stop()
    time.sleep(4)
    print("done")
