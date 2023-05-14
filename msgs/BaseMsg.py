from typing import TypedDict
from Address import Address
from enum import Enum

class BaseMsg(TypedDict):
    ...

class BaseReq(BaseMsg):
    ...

class RespStatus(Enum):
    SUCCESS = "success"
    REDIRECTED = "redirected"
    FAILED = "failed"

class BaseResp(BaseMsg):
    status: RespStatus
    address: Address
