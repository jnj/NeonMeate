import _thread
import queue
import sched
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from ..ui.toolkit import gtk_main


def signal_subcribe_on_main(connect_fn, signal_name, callback, *args):
    """
    Connects to a signal, but decorates the handler function
    such that it will be called by the main GLib thread.
    """

    @gtk_main
    def run_on_main_thread(obj, *a):
        callback(obj, *a)

    connect_fn(signal_name, run_on_main_thread, *args)


class EventLoopThread(threading.Thread):
    def __init__(self, error_handler):
        super(EventLoopThread, self).__init__(name='EventLoop', daemon=True)
        self._queue = queue.SimpleQueue()
        self._running = False
        self._error_handler = error_handler

    def add(self, action):
        self._queue.put(action)

    def run(self):
        self._running = True
        while self._running:
            action = self._queue.get()
            if action:
                try:
                    action()
                except BaseException as e:
                    self._error_handler(e)

    def stop(self):
        self._running = False


class ScheduledExecutor:
    """
    An event loop that supports running tasks as well as
    scheduling tasks in the future. This also contains a
    thread pool, which can have jobs submitted to it.
    The thread pool does not use the event loop thread.
    """

    def __init__(self, event_loop_err_handler, executor_err_handler):
        self._thread = EventLoopThread(event_loop_err_handler)
        self._scheduler = sched.scheduler(timefunc=time.monotonic)
        self._exec_error_handler = executor_err_handler
        self._executor = ThreadPoolExecutor()
        self._nullScheduledTask = NullCancelable()
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

    def execute_async(self, task, *args, **kwargs):
        """
        Submits a task to the thread pool, not to the event loop
        :return: a future
        """

        def wrapped():
            try:
                return task(*args, **kwargs)
            except BaseException as e:
                self._exec_error_handler.on_exception(e)

        return self._executor.submit(wrapped)

    def execute(self, action):
        """
        Executes a task on the event loop thread.
        """
        self._thread.add(action)

    def schedule(self, delay, action):
        """
        Schedules a task on the event loop thread.
        """
        if self._stopped:
            return self._nullScheduledTask

        return ScheduledTask(
            delay,
            action,
            self._scheduler,
            self._executor,
            self._thread,
            False
        )

    def schedule_periodic(self, delay, action):
        """
        Schedules a repeating task on the event loop thread.
        """
        if self._stopped:
            return self._nullScheduledTask

        return ScheduledTask(
            delay,
            action,
            self._scheduler,
            self._executor,
            self._thread,
            True
        )


class NullCancelable:
    def __init__(self):
        pass

    def cancel(self):
        pass


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
