from msgs.BaseMsg import BaseReq, BaseResp

class CommitLogReq(BaseReq):
    commit_length: int

class CommitLogResp(BaseResp):
    ...