from msgs.BaseMsg import BaseReq, BaseResp
from Address import Address
from typing import Any, List

class ApplyMembershipReq(BaseReq):
    ip: str
    port: int
    insert: bool


class ApplyMembershipResp(BaseResp):
    log: List[str]
    cluster_addr_list: List[Address]
