import threading
from typing import Callable


class SetInterval:
    def __init__(self, func: Callable, interval: float):
        self.func = func
        self.interval = interval
        self.stopped = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def _run(self):
        while not self.stopped.wait(self.interval):
            self.func()

    def stop(self):
        self.stopped.set()

    def reset(self, new_interval=None):
        if new_interval is not None:        
            self.interval = new_interval

        self.stopped.set()
        self.stopped.clear()
        self.start()
