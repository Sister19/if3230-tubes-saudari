from structs.Log import Log
import re

class MessageQueue:
    def __init__(self):
        self.queue = []

    def __enqueue(self, message):
        self.queue.append(message)

    def __dequeue(self):
        if len(self.queue) == 0:
            return None
        return self.queue.pop(0)
    
    def executing_log(self, log: Log, i: int):
        # get the value inside the command queue
        raw_command = log[i]['command']
        command_queue = re.search(r'\bqueue\((.*?)\)', raw_command)

        if (command_queue != None and command_queue.group(1)):
            self.__enqueue(command_queue.group(1))

        elif (raw_command == "dequeue()"):
            result = self.__dequeue()
            log[i]['value'] = result