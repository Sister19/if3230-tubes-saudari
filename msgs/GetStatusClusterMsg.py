from msgs.BaseMsg import BaseReq, BaseResp
from Address import Address
from typing import Any, List
from structs.NodeStatus import NodeStatus

class GetStatusClusterReq(BaseReq):
  ...


class GetStatusClusterResp(BaseResp):
  data: List[NodeStatus]
