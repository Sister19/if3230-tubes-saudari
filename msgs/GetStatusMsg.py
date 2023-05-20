from msgs.BaseMsg import BaseReq, BaseResp
from Address import Address
from typing import Any, List
from structs.NodeStatus import NodeStatus

class GetStatusReq(BaseReq):
  ...


class GetStatusResp(BaseResp):
  data: NodeStatus
