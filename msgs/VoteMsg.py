from msgs.BaseMsg import BaseReq, BaseResp
from Address import Address
from typing import Any, List

class VoteReq(BaseReq):
  voted_for: Address
  term: int
  log_length: int
  last_term: int


class VoteResp(BaseResp):
  node_addr: Address
  current_term: int
  granted: bool
