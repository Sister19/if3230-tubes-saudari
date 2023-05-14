from msgs.BaseMsg import BaseReq, BaseResp
from Address import Address
from enum import Enum
from typing import List
from structs.Log import Log

# TODO : class HeartbeatReq
class HeartbeatReq(BaseReq):
    leader_addr: Address
    term: int
    prefix_len: int
    prefix_term: int
    commit_length: int
    suffix: List[Log]

class HeartbeatRespType(Enum):
    ACK = "ack"

class HeartbeatResp(BaseResp):
    heartbeat_response: HeartbeatRespType
