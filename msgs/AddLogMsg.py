from msgs.BaseMsg import BaseReq, BaseResp

class AddLogReq(BaseReq):
    command: str
    value: str
    term: str

class AddLogResp(BaseResp):
    ...