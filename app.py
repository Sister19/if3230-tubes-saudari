from structs.Log import Log
import re

class MessageQueue:
    ALLOWED_COMMANDS = ["enqueue", "dequeue"]

    def __init__(self):
        self.queue = []

    def __enqueue(self, message):
        self.queue.append(message)

    def __dequeue(self):
        if len(self.queue) == 0:
            return None
        return self.queue.pop(0)
    
    def executing_log(self, log: Log):
        # get the value inside the command queue
        raw_command = log['command']

        splitted = raw_command.split('(')
        command = splitted[0]
        value = splitted[1][:-1]

        if command not in self.ALLOWED_COMMANDS:
            log['value'] = "Invalid command"
            return
        
        if command == "enqueue":
            log['value'] = self.__enqueue(value)
        elif command == "dequeue":
            log['value'] = self.__dequeue()
        else:
            log['value'] = "Not implemented yet"

    def data(self):
        return self.queue
