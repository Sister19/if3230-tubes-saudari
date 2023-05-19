import threading
from typing import Callable

class ResettableInterval:
    def __init__(self, interval: int, function: Callable, args=None, kwargs=None):
        self.interval = interval
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.timer = None
        self.is_running = False
        self.first_run = True

    def _run(self):
        self.is_running = False
        self.start()
        if not self.first_run:
            self.first_run = False
            self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self.timer = threading.Timer(self.interval, self._run)
            self.timer.start()
            self.is_running = True

    def stop(self):
        self.timer.cancel()
        self.is_running = False

    def reset(self):
        self.stop()
        self.first_run = True
        self.start()
