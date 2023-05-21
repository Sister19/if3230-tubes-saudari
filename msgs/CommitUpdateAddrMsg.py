from msgs.BaseMsg import BaseReq, BaseResp
from Address import Address
from enum import Enum
from typing import List
from structs.Log import Log

class CommitUpdateAddrReq(BaseReq):
    ip: str
    port: int
    insert: bool

class CommitUpdateAddrResp(BaseResp):
    ...
