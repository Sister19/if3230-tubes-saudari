from msgs.BaseMsg import BaseReq, BaseResp
from Address import Address
from typing import Any, List
from structs.NodeStatus import NodeStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from RaftNode import RaftNode

class GetClusterReq(BaseReq):
  ...


class GetClusterResp(BaseResp):
  data: List["RaftNode.ClusterElmt"]
