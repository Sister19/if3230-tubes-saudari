from typing import TypedDict
from enums.Command import Command


class Log(TypedDict):
    index: int
    term: int
    command: Command
    value: str
    is_committed: bool
    # is_applied: bool
