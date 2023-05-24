import json
from msgs.BaseMsg import BaseMsg

class MsgParser:
    def serialize(self, msg: BaseMsg) -> str:
        return json.dumps(msg)

    def deserialize(self, json_msg: str) -> BaseMsg:
        return json.loads(json_msg)

