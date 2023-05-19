from typing import Callable
import threading

def set_interval(func: Callable, interval: int):
    def fn_wrapper():
        set_interval(func, interval)
        func()
    t = threading.Timer(interval, fn_wrapper)
    t.start()
    return t    
