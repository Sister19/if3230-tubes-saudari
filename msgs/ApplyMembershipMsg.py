from msgs.BaseMsg import BaseMsg
from Address import Address
from typing import Any, List

class ApplyMembershipReq(BaseMsg):
    ip: str
    port: int


class ApplyMembershipResp(BaseMsg):
    status: str
    address: Address
    log: List[str]
    cluster_addr_list: List[Address]
