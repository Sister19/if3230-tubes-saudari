from msgs.BaseMsg import BaseReq, BaseResp

class ExecuteReq(BaseReq):
    command: str
    value: str

class ExecuteResp(BaseResp):
    data: dict

