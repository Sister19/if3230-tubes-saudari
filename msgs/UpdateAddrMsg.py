from msgs.BaseMsg import BaseReq, BaseResp
from Address import Address
from enum import Enum
from typing import List
from structs.Log import Log

class UpdateAddrReq(BaseReq):
    ip: str
    port: int
    insert: bool

class UpdateAddrResp(BaseResp):
    ...
