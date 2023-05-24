from msgs.BaseMsg import BaseReq, BaseResp
from Address import Address
from enum import Enum
from typing import List
from structs.Log import Log

class RequestLogReq(BaseReq):
    ...

class RequestLogResp(BaseResp):
    log: List[Log]
