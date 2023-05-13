from msgs.BaseMsg import BaseMsg
from Address import Address
from typing import Any, List

class VoteReq(BaseMsg):
  voted_for: Address
  term: int
  log_length: int
  last_term: int


class VoteResp(BaseMsg):
  status: str
  address: Address
  node_addr: Address
  term: int
  flag: bool
