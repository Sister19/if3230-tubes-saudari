from typing import TypedDict, TypeVar, Generic, Any
from Address import Address
import threading
import json
import asyncio
T = TypeVar('T', bound=TypedDict)

class StableStorage(Generic[T]):
    def __init__(self, addr: Address):
        self.id = self.__id_from_addr(addr)
        self.path = f"persistence/{self.id}.json"
        self.lock = threading.Lock()

    def __enter__(self):
        print("Acquire stable storage lock")
        self.lock.acquire()
        return self.load()
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()
        print("Release stable storage lock")

    def __id_from_addr(self, addr: Address):
        return f"{addr.ip}_{addr.port}"

    def __store(self, data: str):
        with open(self.path, 'w') as f:
            f.write(data)
    
    def __load(self):
        with open(self.path, 'r') as f:
            return f.read()
    
    def load(self) -> T:
        return json.loads(self.__load())

    def storeAll(self, data: T) -> T:
        str_data = json.dumps(data)
        self.__store(str_data)
        return data
    
    def try_load(self):
        try:
            return self.load()
        except:
            return None